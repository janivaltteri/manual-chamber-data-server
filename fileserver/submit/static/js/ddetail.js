'use strict';

$('document').ready( () => {

  console.log(fsid_text);

  // fdetail

  $('#status_change').click(function(e){
    //let fullpath = $(location).attr('href');
    //let splitpath = fullpath.split("/");
    //let uname = splitpath[5];
    //let num = splitpath[6];
    let fsid = parseInt(fsid_text);
    $.ajax({
      type: 'GET',
      data: {'fsid': fsid},
      url: '/submit/statuschange/',
      success: (msg) => {
	console.log(msg);
	console.log('success');
	location.reload();
      },
      error: (msg) => {
	console.log(msg);
	console.log('error');
      }
    });
  });

  // ddetail

  let ctx_co2 = null;
  if(document.getElementById('co2')){
    ctx_co2 = document.getElementById('co2').getContext('2d');
  }

  $('#nappi').click(function(e){
    //let fullpath = $(location).attr('href');
    //let splitpath = fullpath.split("/");
    //let uname = splitpath[5];
    //let num = splitpath[6];
    let fsid = parseInt(fsid_text);
    $.ajax({
      type: 'GET',
      data: {'fsid': fsid},
      url: '/submit/dataget/',
      success: (msg) => {
	console.log(msg);
	console.log('success');
	draw_co2(msg['time'],msg['co2']);
      },
      error: (msg) => {
	console.log(msg);
	console.log('error');
      }
    });
  });

  function draw_co2(t,co2){
    var myChart = new Chart(ctx_co2, {
      type: 'line',
      data: {
	labels: t,
        datasets: [{
          label: 'CO2',
	  borderColor: 'rgb(75, 192, 192)',
	  fill: false,
          data: co2,
        }]
      },
      options: {
        scales: {
          y: {
            beginAtZero: false,
	    min: 0.0,
	    max: 800.0
          }
        }
      }
    });
  };
  
});
