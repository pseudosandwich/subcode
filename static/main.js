var substringMatcher = function(strs) {
  return function findMatches(q, cb) {
    var matches, substrRegex;

    // an array that will be populated with substring matches
    matches = [];

    // regex used to determine if a string contains the substring `q`
    substrRegex = new RegExp(q, 'i');

    // iterate through the pool of strings and for any string that
    // contains the substring `q`, add it to the `matches` array
    $.each(strs, function(i, str) {
      if (substrRegex.test(str)) {
        // the typeahead jQuery plugin expects suggestions to a
        // JavaScript object, refer to typeahead docs for more info
        matches.push({ value: str });
      }
    });

    cb(matches);
  };
};

var languages = ['Swift', 'C', 'Lisp', 'XML'];

$('#language .typeahead').typeahead({
  hint: true,
  highlight: true,
  minLength: 1
},
{
  name: 'languages',
  displayKey: 'value',
  source: substringMatcher(languages)
});

$('form').submit(function(e) {
  //alert('test');
  var email = $('input[name=email]').val();
  if(!validateEmail(email)) {
    e.preventDefault();
    return;
  }
  var language = $('select[name=language]').val();
  if(!language) {
    e.preventDefault();
    return;
  }
});

function validateEmail(email) {
  var re = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
  return re.test(email);
}
