// Generated by CoffeeScript 1.6.1
(function() {
  var Histogram, root;

  root = typeof exports !== "undefined" && exports !== null ? exports : this;

  Histogram = (function() {

    function Histogram(sample_list, sample_group) {
      this.sample_list = sample_list;
      this.sample_group = sample_group;
      this.sort_by = "name";
      this.format_count = d3.format(",.0f");
      this.get_sample_vals();
      this.margin = {
        top: 10,
        right: 30,
        bottom: 30,
        left: 30
      };
      this.plot_width = 960 - this.margin.left - this.margin.right;
      this.plot_height = 500 - this.margin.top - this.margin.bottom;
      this.x_buffer = this.plot_width / 20;
      this.y_buffer = this.plot_height / 20;
      this.y_min = d3.min(this.sample_vals);
      this.y_max = d3.max(this.sample_vals) * 1.1;
      this.plot_height -= this.y_buffer;
      this.create_x_scale();
      this.get_histogram_data();
      this.create_y_scale();
      this.svg = this.create_svg();
      this.create_graph();
    }

    Histogram.prototype.get_sample_vals = function() {
      var sample;
      return this.sample_vals = (function() {
        var _i, _len, _ref, _results;
        _ref = this.sample_list;
        _results = [];
        for (_i = 0, _len = _ref.length; _i < _len; _i++) {
          sample = _ref[_i];
          if (sample.value !== null) {
            _results.push(sample.value);
          }
        }
        return _results;
      }).call(this);
    };

    Histogram.prototype.create_svg = function() {
      var svg;
      svg = d3.select("#histogram").append("svg").attr("class", "histogram").attr("width", this.plot_width + this.margin.left + this.margin.right).attr("height", this.plot_height + this.margin.top + this.margin.bottom).append("g").attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");
      return svg;
    };

    Histogram.prototype.create_x_scale = function() {
      var min_domain;
      console.log("min/max:", d3.min(this.sample_vals) + "," + d3.max(this.sample_vals));
      if (d3.min(this.sample_vals) < 0) {
        min_domain = d3.min(this.sample_vals);
      } else {
        min_domain = 0;
      }
      return this.x_scale = d3.scale.linear().domain([min_domain, parseFloat(d3.max(this.sample_vals))]).range([0, this.plot_width]);
    };

    Histogram.prototype.get_histogram_data = function() {
      console.log("sample_vals:", this.sample_vals);
      this.histogram_data = d3.layout.histogram().bins(this.x_scale.ticks(20))(this.sample_vals);
      return console.log("histogram_data:", this.histogram_data[0]);
    };

    Histogram.prototype.create_y_scale = function() {
      var _this = this;
      return this.y_scale = d3.scale.linear().domain([
        0, d3.max(this.histogram_data, function(d) {
          return d.y;
        })
      ]).range([this.plot_height, 0]);
    };

    Histogram.prototype.create_graph = function() {
      this.add_x_axis();
      return this.add_bars();
    };

    Histogram.prototype.add_x_axis = function() {
      var x_axis;
      x_axis = d3.svg.axis().scale(this.x_scale).orient("bottom");
      return this.svg.append("g").attr("class", "x axis").attr("transform", "translate(0," + this.plot_height + ")").call(x_axis);
    };

    Histogram.prototype.add_y_axis = function() {
      var y_axis;
      return y_axis = d3.svg.axis().scale(this.y_scale).orient("left").ticks(5);
    };

    Histogram.prototype.add_bars = function() {
      var bar,
        _this = this;
      console.log("bar_width:", this.x_scale(this.histogram_data[0].dx));
      bar = this.svg.selectAll(".bar").data(this.histogram_data).enter().append("g").attr("class", "bar").attr("transform", function(d) {
        return "translate(" + _this.x_scale(d.x) + "," + _this.y_scale(d.y) + ")";
      });
      bar.append("rect").attr("x", 1).attr("width", this.x_scale(this.histogram_data[0].x + this.histogram_data[0].dx) - 1).attr("height", function(d) {
        return _this.plot_height - _this.y_scale(d.y);
      });
      return bar.append("text").attr("dy", ".75em").attr("y", 6).attr("x", this.x_scale(this.histogram_data[0].dx) / 2).attr("text-anchor", "middle").style("fill", "#fff").text(function(d) {
        var bar_height;
        bar_height = _this.plot_height - _this.y_scale(d.y);
        if (bar_height > 20) {
          return _this.format_count(d.y);
        }
      });
    };

    return Histogram;

  })();

  root.Histogram = Histogram;

}).call(this);
