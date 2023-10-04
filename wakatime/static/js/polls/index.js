$(function () {
  new (Backbone.View.extend({
    el: $('#main-content'),
    events: {
      'click .markdown-popup': 'clickMarkdown',
    },
    templates: {
      markdown: $('#markdown-template').html(),
    },
    clickMarkdown: function (e) {
      e && e.preventDefault();
      var $link = $(e.target);
      if (!$link.attr('data-markdown')) $link = $link.parent();
      utils.showModal({
        $el: this.$el,
        title: 'Markdown',
        body: Mustache.render(this.templates.markdown, {
          content: $link.attr('data-markdown'),
        }),
        hide_buttons: true,
        after_shown: function ($modal) {
          $modal.find('textarea').select();
        },
      });
    },
  }))();
});
