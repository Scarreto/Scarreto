## Copyright (C) University of Tennessee Health Science Center, Memphis, TN.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# This program is available from Source Forge: at GeneNetwork Project
# (sourceforge.net/projects/genenetwork/).
#
# Contact Dr. Robert W. Williams at rwilliams@uthsc.edu
#
#
# This module is used by GeneNetwork project (www.genenetwork.org)

from __future__ import absolute_import, print_function, division

import sys
# sys.path.append(".")   Never do this in a webserver!

import string
import cPickle
import os
import datetime
import time
import pp
import math
import collections
import resource

import numpy as np
import scipy

from rpy2.robjects.packages import importr
import rpy2.robjects as robjects

from pprint import pformat as pf

import reaper

import redis
Redis = redis.StrictRedis()

from utility.THCell import THCell
from utility.TDCell import TDCell
from base.trait import GeneralTrait
from base import data_set
from utility import webqtlUtil, helper_functions, corr_result_helpers
from db import webqtlDatabaseFunction
import utility.webqtlUtil #this is for parallel computing only.
from wqflask.correlation import correlation_functions
from utility.benchmark import Bench

from MySQLdb import escape_string as escape

from pprint import pformat as pf

from flask import Flask, g, url_for

import utility.logger
logger = utility.logger.getLogger(__name__ )

class CorrelationMatrix(object):

    def __init__(self, start_vars):
        trait_db_list = [trait.strip() for trait in start_vars['trait_list'].split(',')]

        helper_functions.get_trait_db_obs(self, trait_db_list)

        self.all_sample_list = []
        self.traits = []
        self.insufficient_shared_samples = False
        self.do_PCA = True
        this_group = self.trait_list[0][1].group.name #ZS: Getting initial group name before verifying all traits are in the same group in the following loop
        for trait_db in self.trait_list:
            if trait_db[1].group.name != this_group:
                self.insufficient_shared_samples = True
                break
            else:
                this_group = trait_db[1].group.name
            this_trait = trait_db[0]
            self.traits.append(this_trait)
            this_sample_data = this_trait.data

            for sample in this_sample_data:
                if sample not in self.all_sample_list:
                    self.all_sample_list.append(sample)

        if self.insufficient_shared_samples:
            pass
        else:
            self.sample_data = []
            for trait_db in self.trait_list:
                this_trait = trait_db[0]
                this_sample_data = this_trait.data

                this_trait_vals = []
                for sample in self.all_sample_list:
                    if sample in this_sample_data:
                        this_trait_vals.append(this_sample_data[sample].value)
                    else:
                        this_trait_vals.append('')
                self.sample_data.append(this_trait_vals)

            if len(this_trait_vals) < len(self.trait_list): #Shouldn't do PCA if there are more traits than observations/samples
                self.do_PCA = False

            self.lowest_overlap = 8 #ZS: Variable set to the lowest overlapping samples in order to notify user, or 8, whichever is lower (since 8 is when we want to display warning)

            self.corr_results = []
            self.pca_corr_results = []
            self.shared_samples_list = self.all_sample_list
            for trait_db in self.trait_list:
                this_trait = trait_db[0]
                this_db = trait_db[1]

                this_db_samples = this_db.group.all_samples_ordered()
                this_sample_data = this_trait.data

                corr_result_row = []
                pca_corr_result_row = []
                is_spearman = False #ZS: To determine if it's above or below the diagonal
                for target in self.trait_list:
                    target_trait = target[0]
                    target_db = target[1]
                    target_samples = target_db.group.all_samples_ordered()
                    target_sample_data = target_trait.data

                    this_trait_vals = []
                    target_vals = []
                    for index, sample in enumerate(target_samples):
                        if (sample in this_sample_data) and (sample in target_sample_data):
                            sample_value = this_sample_data[sample].value
                            target_sample_value = target_sample_data[sample].value
                            this_trait_vals.append(sample_value)
                            target_vals.append(target_sample_value)
                        else:
                            if sample in self.shared_samples_list:
                                self.shared_samples_list.remove(sample)

                    this_trait_vals, target_vals, num_overlap = corr_result_helpers.normalize_values(this_trait_vals, target_vals)

                    if num_overlap < self.lowest_overlap:
                        self.lowest_overlap = num_overlap
                    if num_overlap == 0:
                        corr_result_row.append([target_trait, 0, num_overlap])
                        pca_corr_result_row.append(0)
                    else:
                        pearson_r, pearson_p = scipy.stats.pearsonr(this_trait_vals, target_vals)
                        if is_spearman == False:
                            sample_r, sample_p = pearson_r, pearson_p
                            if sample_r == 1:
                                is_spearman = True
                        else:
                            sample_r, sample_p = scipy.stats.spearmanr(this_trait_vals, target_vals)

                        corr_result_row.append([target_trait, sample_r, num_overlap])
                        pca_corr_result_row.append(pearson_r)

                self.corr_results.append(corr_result_row)
                self.pca_corr_results.append(pca_corr_result_row)

            self.trait_data_array = []
            for trait_db in self.trait_list:
                this_trait = trait_db[0]
                this_db = trait_db[1]
                this_db_samples = this_db.group.all_samples_ordered()
                this_sample_data = this_trait.data

                this_trait_vals = []
                for index, sample in enumerate(this_db_samples):
                    if (sample in this_sample_data) and (sample in self.shared_samples_list):
                        sample_value = this_sample_data[sample].value
                        this_trait_vals.append(sample_value)
                self.trait_data_array.append(this_trait_vals)

            corr_result_eigen = np.linalg.eig(np.array(self.pca_corr_results))
            corr_eigen_value, corr_eigen_vectors = sortEigenVectors(corr_result_eigen)

            groups = []
            for sample in self.all_sample_list:
                groups.append(1)

            try:
                if self.do_PCA == True:
                    self.pca_works = "True"
                    self.pca_trait_ids = []
                    pca = self.calculate_pca(range(len(self.traits)), corr_eigen_value, corr_eigen_vectors)
                    self.loadings_array = self.process_loadings()
                else:
                    self.pca_works = "False"
            except:
                self.pca_works = "False"

            self.js_data = dict(traits = [trait.name for trait in self.traits],
                                groups = groups,
                                cols = range(len(self.traits)),
                                rows = range(len(self.traits)),
                                samples = self.all_sample_list,
                                sample_data = self.sample_data,)
            #                    corr_results = [result[1] for result in result_row for result_row in self.corr_results])
        
    def get_trait_db_obs(self, trait_db_list):

        self.trait_list = []
        for i, trait_db in enumerate(trait_db_list):
            if i == (len(trait_db_list) - 1):
                break
            trait_name, dataset_name = trait_db.split(":")
            #print("dataset_name:", dataset_name)
            dataset_ob = data_set.create_dataset(dataset_name)
            trait_ob = GeneralTrait(dataset=dataset_ob,
                                   name=trait_name,
                                   cellid=None)
            self.trait_list.append((trait_ob, dataset_ob))

    def calculate_pca(self, cols, corr_eigen_value, corr_eigen_vectors):
        base = importr('base')
        stats = importr('stats')

        corr_results_to_list = robjects.FloatVector([item for sublist in self.pca_corr_results for item in sublist])

        m = robjects.r.matrix(corr_results_to_list, nrow=len(cols))
        eigen = base.eigen(m)
        pca = stats.princomp(m, cor = "TRUE")
        self.loadings = pca.rx('loadings')
        self.scores = pca.rx('scores')
        self.scale = pca.rx('scale')

        trait_array = zScore(self.trait_data_array)
        trait_array_vectors = np.dot(corr_eigen_vectors, trait_array)

        pca_traits = []
        for i, vector in enumerate(trait_array_vectors):
            #ZS: Check if below check is necessary
            #if corr_eigen_value[i-1] > 100.0/len(self.trait_list):
            pca_traits.append((vector*-1.0).tolist())

        this_group_name = self.trait_list[0][1].group.name
        temp_dataset = data_set.create_dataset(dataset_name = "Temp", dataset_type = "Temp", group_name = this_group_name)
        temp_dataset.group.get_samplelist()
        for i, pca_trait in enumerate(pca_traits):
            trait_id = "PCA" + str(i+1) + "_" + temp_dataset.group.species + "_" + this_group_name + "_" + datetime.datetime.now().strftime("%m%d%H%M%S")
            this_vals_string = ""
            position = 0
            for sample in temp_dataset.group.all_samples_ordered():
                if sample in self.shared_samples_list:
                    this_vals_string += str(pca_trait[position])
                    this_vals_string += " "
                    position += 1
                else:
                    this_vals_string += "x "
            this_vals_string = this_vals_string[:-1]

            Redis.set(trait_id, this_vals_string)
            self.pca_trait_ids.append(trait_id)

        return pca

    def process_loadings(self):
        loadings_array = []
        loadings_row = []
        for i in range(len(self.trait_list)):
            loadings_row = []
            if len(self.trait_list) > 2:
               the_range = 3
            else:
               the_range = 2
            for j in range(the_range):
                position = i + len(self.trait_list)*j
                loadings_row.append(self.loadings[0][position])
            loadings_array.append(loadings_row)
        return loadings_array

def zScore(trait_data_array):
    NN = len(trait_data_array[0])
    if NN < 10:
        return trait_data_array
    else:
        i = 0
        for data in trait_data_array:
            N = len(data)
            S = reduce(lambda x,y: x+y, data, 0.)
            SS = reduce(lambda x,y: x+y*y, data, 0.)
            mean = S/N
            var = SS - S*S/N
            stdev = math.sqrt(var/(N-1))
            if stdev == 0:
                stdev = 1e-100
            data2 = map(lambda x:(x-mean)/stdev,data)
            trait_data_array[i] = data2
            i += 1
        return trait_data_array

def sortEigenVectors(vector):
    try:
        eigenValues = vector[0].tolist()
        eigenVectors = vector[1].T.tolist()
        combines = []
        i = 0
        for item in eigenValues:
            combines.append([eigenValues[i],eigenVectors[i]])
            i += 1
        combines.sort(webqtlUtil.cmpEigenValue)
        A = []
        B = []
        for item in combines:
            A.append(item[0])
            B.append(item[1])
        sum = reduce(lambda x,y: x+y, A, 0.0)
        A = map(lambda x:x*100.0/sum, A) 
        return [A, B]
    except:
        return []