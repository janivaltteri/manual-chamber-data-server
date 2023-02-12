'use strict';

$('document').ready( () => {

  $(".trim_s_button").click(function() {
    let id_num = parseInt($(this).data("id"));
    let gas_num = parseInt($(this).data("gas"));
    /*
    let element = $(".test")
    .find('.trim_s_entry,[data-id="' + id_num + '"],[data-gas="' + gas_num + '"]');
    */
    let value = parseInt($("#trim_" + get_gas_name(gas_num) + "_s_entry" + id_num).val());
    console.log("called trim_s_button id ",id_num," value ",value," gas ",gas_num);
    set_trim_start(id_num,gas_num,value);
  });

  // todo: write as above
  $(".trim_e_button").click(function() {
    let id_num = parseInt($(this).data("id"));
    let gas_num = parseInt($(this).data("gas"));
    let value = parseInt($("#trim_" + get_gas_name(gas_num) + "_e_entry" + id_num).val());
    console.log("called trim_e_button id ",id_num," value ",value," gas ",gas_num);
    set_trim_end(id_num,gas_num,value);
  });

  $(".personal_flux_button").click(function() {
    let id_num = parseInt($(this).data("id"));
    let gas_num = parseInt($(this).data("gas"));
    let gas_name = get_gas_name(gas_num);
    let start_val = parseInt($("#trim_" + gas_name + "_s_entry" + id_num).val());
    let end_val = parseInt($("#trim_" + gas_name + "_e_entry" + id_num).val());
    let bad_val = $('input[name="' + gas_name + 'radio' + id_num + '"]:checked').val();
    console.log("personal flux ",id_num," with start ",start_val," end ",end_val,
		" badness ",bad_val," gas ",gas_num);
    $.ajax({
      type: "POST", url: "/ajax/personal",
      contentType: 'application/json;charset=UTF-8',
      data: JSON.stringify({'series_id':        id_num,
			    'gas':              gas_num,
			    'trim_start_value': start_val,
			    'trim_end_value':   end_val,
			    'bad_value':        bad_val}),
      success: function(msg){
	console.log(msg);
	$("#trim_" + gas_name + "_head_val" + id_num).text(start_val);
	$("#trim_" + gas_name + "_tail_val" + id_num).text(end_val);
	$("#fluxtext" + gas_name + id_num).text(msg.new_lin_flux.toFixed(9));
	$("#rsumtext" + gas_name + id_num).text(msg.new_rsum);
	$("#badtext" + gas_name + id_num).text(msg.new_bad);
	set_trim_start(id_num,gas_num,start_val);
	set_trim_end(id_num,gas_num,end_val);
	set_slope(id_num, gas_num, msg.new_intercept, msg.new_slope);
      },
      error: function(msg){ console.log(msg); }
    });
  });

  $(".clear_personal_button").click(function() {
    let id_num = parseInt($(this).data("id"));
    let gas_num = parseInt($(this).data("gas"));
    let gas_name = get_gas_name(gas_num);
    console.log("clearing personal flux ",id_num," gas ",gas_num);
    $.ajax({
      type: "POST", url: "/ajax/clear",
      contentType: 'application/json;charset=UTF-8',
      data: JSON.stringify({'series_id':        id_num,
			    'gas':              gas_num}),
      success: function(msg){
	console.log(msg);
	$("#trim_" + gas_name + "_head_val" + id_num).text('NA');
	$("#trim_" + gas_name + "_tail_val" + id_num).text('NA');
	$("#fluxtext" + gas_name + id_num).text('NA');
	$("#rsumtext" + gas_name + id_num).text('NA');
	$("#badtext" + gas_name + id_num).text('NA');
	set_trim_start(id_num,gas_num,0);
	set_trim_end(id_num,gas_num,0);
	set_slope(id_num, gas_num, 0, 0);
      },
      error: function(msg){ console.log(msg); }
    });
  });
  
  function get_gas_name(g){
    let gas_name;
    if(g == 1){
      gas_name = 'co2';
    }else if(g == 2){
      gas_name = 'ch4';
    }else if(g == 3){
      gas_name = 'n2o';
    }else{
      gas_name = '';
    }
    return gas_name;
  }

  function set_trim_start(id,g,v){
    let index = -1;
    for(let i = 0; i < mat.length; i++){
      if(mat[i].id == id){
	index = i;
      }
    }
    if(index < 0){
      console.log("error in set_trim_start");
      return;
    }
    let gas_name = get_gas_name(g);
    let tline = d3.select("#trim_h_" + gas_name + "_" + id);;
    tline.attr("x1", x_axes[index](0 + v))
      .attr("x2", x_axes[index](0 + v));
  }

  function set_trim_end(id,g,v){
    let index = -1;
    for(let i = 0; i < mat.length; i++){
      if(mat[i].id == id){
	index = i;
      }
    }
    if(index < 0){
      console.log("error in set_trim_end");
      return;
    }
    let gas_name = get_gas_name(g);
    let tline = d3.select("#trim_t_" + gas_name + "_" + id);
    tline.attr("x1", x_axes[index](x_maxs[index] - v))
      .attr("x2", x_axes[index](x_maxs[index] - v));
  }

  function set_slope(id,g,ic,sl){
    let index = -1;
    for(let i = 0; i < mat.length; i++){
      if(mat[i].id == id){
	index = i;
      }
    }
    if(index < 0){
      console.log("error in set_slope");
      return;
    }
    let gas_name = get_gas_name(g);
    let tline = d3.select("#slope_" + gas_name + "_" + id);
    let new_y1;
    let new_y2;
    if(g == 1){
      // todo: are these two not used?
      new_y1 = y_axes_co2[index](ic);
      new_y2 = y_axes_co2[index](ic + x_maxs[index] * sl);
      tline.attr("y1", y_axes_co2[index](ic))
	.attr("y2", y_axes_co2[index](ic + x_maxs[index] * sl));
    }else if(g == 2){
      new_y1 = y_axes_ch4[index](ic);
      new_y2 = y_axes_ch4[index](ic + x_maxs[index] * sl);
      tline.attr("y1", y_axes_ch4[index](ic))
	.attr("y2", y_axes_ch4[index](ic + x_maxs[index] * sl));
    }else if(g == 3){
      new_y1 = y_axes_n2o[index](ic);
      new_y2 = y_axes_n2o[index](ic + x_maxs[index] * sl);
      tline.attr("y1", y_axes_n2o[index](ic))
	.attr("y2", y_axes_n2o[index](ic + x_maxs[index] * sl));
    }else{
      // signal error
      return;
    }
  }
  
});

