function DropDown(el) {
  this.dd = el;
  this.placeholder = this.dd.children('span');
  this.opts = this.dd.find('ul.dropdown > li');
  this.val = '';
  this.index = -1;
  this.initEvents();
}

DropDown.prototype = {
  initEvents : function() {
    var obj = this;

    obj.dd.on('click', function(event){
      $(this).toggleClass('active');
      return false;
    });

    obj.opts.on('click',function(){
      var opt = $(this);
      obj.val = opt.text();
      obj.index = opt.index();
      obj.placeholder.text('Language: ' + obj.val);
    });
  },
  getValue : function() {
    return this.val;
  },
  getIndex : function() {
    return this.index;
  }
}

var dd;

$(function() {

  dd = new DropDown( $('#lang') );

  $(document).click(function() {
    // all dropdowns
    $('#lang').removeClass('active');
  });

  $(document).ready(function() {
    $('#email').focus();
  });
});

$('form').submit(function(e) {
  //alert('test');
  var email = $('input[name=email]').val();
  if(!validateEmail(email)) {
    e.preventDefault();
    return;
  }
  var language = dd.getValue();
  if(!language) {
    e.preventDefault();
    return;
  }

  $('<input />').attr('type', 'hidden')
          .attr('name', "language")
          .attr('value', language)
          .appendTo('form');
  return true;

});

function validateEmail(email) {
  var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
  return re.test(email);
}
