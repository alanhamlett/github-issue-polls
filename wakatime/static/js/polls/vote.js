$(function () {
  new (Backbone.View.extend({
    el: $('body'),
    events: {
      'click .unvote': 'clickUnvote',
    },
    templates: {
      markdown: $('#markdown-template').html(),
    },
    clickUnvote: function (e) {
      e && e.preventDefault();
      var $link = $(e.target);
      var choice = $link.attr('data-choice');
      $.ajax({
        url: '/polls/' + bootstrapped.poll_id + '/unvote',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({choice: choice}),
        error: function () {
          window.location.reload();
        },
        success: function () {
          window.location.reload();
        },
      });
    },
  }))();
});
