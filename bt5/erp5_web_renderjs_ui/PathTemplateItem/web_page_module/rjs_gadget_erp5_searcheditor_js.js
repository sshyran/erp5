/*jslint indent: 2, maxerr: 3, maxlen: 100, nomen: true */
/*global window, document, rJS, Handlebars,
  QueryFactory, SimpleQuery, ComplexQuery, Query*/
(function (window, document, rJS, Handlebars,
  QueryFactory, SimpleQuery, ComplexQuery, Query) {
  "use strict";
  var gadget_klass = rJS(window),
    template_element = gadget_klass.__template_element,

    filter_item_template = Handlebars.compile(template_element
                         .getElementById("filter-item-template")
                         .innerHTML),
    filter_template = Handlebars.compile(template_element
                         .getElementById("filter-template")
                         .innerHTML),
    NUMERIC = [
      ["Equals To", "="], ["Greater Than", ">"],
      ["Less Than", "<"], ["Not Greater Than", "<="],
      ["Not Less Than", ">="]
    ],
    OTHER = [
      ["Equals To", "exact_match"],
      ["Contains", "keyword"]
    ],
    DEFAULT = [["Contains", "contain"]],
    PREFIX_COLUMN = 'COLUMN_',
    PREFIX_RAW = 'RAW',
    PREFIX_TEXT = 'TEXT';

  // XXX
  // define input's type according to column's value
  // the way to determiner is not generic
  function isNumericComparison(value) {
    return value.indexOf('date') !== -1 ||
      value.indexOf('quantity') !== -1 ||
      value.indexOf('price') !== -1;
  }

  function createFilterItemTemplate(gadget, query_dict) {
    var operator_default_list = DEFAULT,
      operator_option_list = [],
      column_option_list = [],
      input_type = "search",
      i,
      is_selected;

    if (query_dict.key.indexOf(PREFIX_COLUMN) === 0) {
      if (isNumericComparison(query_dict.key)) {
        operator_default_list = NUMERIC;
        if (query_dict.key.indexOf("date") !== -1) {
          input_type = "date";
        } else {
          input_type = "number";
        }
      } else {
        operator_default_list = OTHER;
      }
    }

    if (!query_dict.operator) {
      // Set the default operator depending of the type of the column
      query_dict.operator = operator_default_list[0][1];
    }
    is_selected = false;
    for (i = 0; i < operator_default_list.length; i += 1) {
      is_selected = is_selected || (query_dict.operator === operator_default_list[i][1]);
      operator_option_list.push({
        text: operator_default_list[i][0],
        value: operator_default_list[i][1],
        selected: (query_dict.operator === operator_default_list[i][1])
      });
    }
    if (!is_selected) {
      // Do not lose the query operator even if it is not handled by the UI
      // Do not try to change it to another value, as it means losing user data
      if (query_dict.key.indexOf(PREFIX_COLUMN) === 0) {
        query_dict.key = query_dict.key.slice(PREFIX_COLUMN.length);
      } else {
        query_dict.key = '';
      }
      query_dict.value = Query.objectToSearchText(new SimpleQuery({
        key: query_dict.key,
        operator: query_dict.operator,
        type: "simple",
        value: query_dict.value
      }));
      query_dict.operator = DEFAULT[0][1];
      query_dict.key = PREFIX_RAW;
      operator_option_list = [{
        text: DEFAULT[0][0],
        value: DEFAULT[0][1],
        selected: true
      }];
    }

    is_selected = false;
    for (i = 0; i < gadget.state.search_column_list.length; i += 1) {
      is_selected = is_selected || (query_dict.key === gadget.state.search_column_list[i][0]);
      column_option_list.push({
        text: gadget.state.search_column_list[i][1],
        value: gadget.state.search_column_list[i][0],
        selected: (query_dict.key === gadget.state.search_column_list[i][0])
      });
    }
    if (!is_selected) {
      throw new Error('SearchEditor: no key found for: ' + query_dict.key);
    }

    return filter_item_template({
      option: column_option_list,
      operator_option: operator_option_list,
      input_value: query_dict.value,
      input_type: input_type
    });
  }

  function getQueryStateFromDOM(gadget) {
    var operator_select = gadget.element.querySelector("select"),
      state = {
        query_list: [],
        operator: operator_select[operator_select.selectedIndex].value
      },
      i,
      filter_item_list = gadget.element.querySelectorAll(".filter_item"),
      select_list;

    for (i = 0; i < filter_item_list.length; i += 1) {
      select_list = filter_item_list[i].querySelectorAll("select");
      state.query_list.push({
        value: filter_item_list[i].querySelector("input").value,
        operator: select_list[1][select_list[1].selectedIndex].value,
        key: select_list[0][select_list[0].selectedIndex].value
      });
    }

    return state;
  }

  function getElementIndex(node) {
    var index = -1;
    while (node) {
      node = node.previousElementSibling;
      index += 1;
    }
    return index;
  }

  gadget_klass
    //////////////////////////////////////////////
    // acquired method
    //////////////////////////////////////////////
    .declareAcquiredMethod("translateHtml", "translateHtml")
    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("trigger", "trigger")

    //////////////////////////////////////////////
    // initialize the gadget content
    //////////////////////////////////////////////
    .declareMethod('render', function (options) {
      var operator = 'AND',
        query_list = [],
        i,
        jio_query,
        len,
        sub_jio_query,
        search_column_list = [],
        search_column_dict = {};

      len = options.search_column_list.length;
      for (i = 0; i < len; i += 1) {
        search_column_dict[options.search_column_list[i][0]] = true;
        search_column_list.push([
          PREFIX_COLUMN + options.search_column_list[i][0],
          options.search_column_list[i][1]
        ]);
      }
      search_column_list.push([PREFIX_TEXT, "Searchable Text"]);
      search_column_list.push([PREFIX_RAW, "Search Expression"]);

      // When the raw query is modified, reset the full gadget
      if (options.extended_search) {
        // Parse the raw query
        try {
          jio_query = QueryFactory.create(options.extended_search);
        } catch (error) {
          // it catch all error, not only search criteria invalid error
          query_list.push({
            key: PREFIX_RAW,
            value: options.extended_search
          });
        }

        if (jio_query instanceof SimpleQuery) {
          if (jio_query.key) {
            if (search_column_dict.hasOwnProperty(jio_query.key)) {
              query_list.push({
                key: PREFIX_COLUMN + jio_query.key,
                value: jio_query.value,
                operator: jio_query.operator
              });
            } else {
              query_list.push({
                key: PREFIX_RAW,
                value: Query.objectToSearchText(jio_query)
              });
            }
          } else {
            query_list.push({
              key: PREFIX_TEXT,
              value: jio_query.value
            });
          }

        } else if (jio_query instanceof ComplexQuery) {
          operator = jio_query.operator;

          len = jio_query.query_list.length;
          for (i = 0; i < len; i += 1) {
            sub_jio_query = jio_query.query_list[i];
            if (sub_jio_query instanceof SimpleQuery) {
              if (sub_jio_query.key) {
                if (search_column_dict.hasOwnProperty(sub_jio_query.key)) {
                  query_list.push({
                    key: PREFIX_COLUMN + sub_jio_query.key,
                    value: sub_jio_query.value,
                    operator: sub_jio_query.operator
                  });
                } else {
                  query_list.push({
                    key: PREFIX_RAW,
                    value: Query.objectToSearchText(sub_jio_query)
                  });
                }
              } else {
                query_list.push({
                  key: PREFIX_TEXT,
                  value: sub_jio_query.value
                });
              }
            } else {
              query_list.push({
                key: PREFIX_RAW,
                value: Query.objectToSearchText(sub_jio_query)
              });
            }
          }
        }
      } else {
        query_list.push({
          key: search_column_list[0][0],
          value: ''
        });
      }

      return this.changeState({
        search_column_list: search_column_list,
        begin_from_key: options.begin_from,
        // [{key: 'title', value: 'Foo', operator: 'like'}]
        query_list: query_list,
        // and/or
        operator: operator
      });
    })

    .onStateChange(function () {
      var gadget = this,
        container = gadget.element.querySelector(".container"),
        div = document.createElement("div"),
        subdiv,
        operator_select,
        filter_item_container,
        i;

      div.innerHTML = filter_template();

      operator_select = div.querySelector("select");
      if (gadget.state.operator === "OR") {
        operator_select.querySelectorAll("option")[1].setAttribute('selected', 'selected');
      }

      filter_item_container = div.querySelector(".filter_item_container");

      for (i = 0; i < gadget.state.query_list.length; i += 1) {
        subdiv = document.createElement("div");
        subdiv.innerHTML = createFilterItemTemplate(gadget, gadget.state.query_list[i]);
        filter_item_container.appendChild(subdiv);
      }

      return gadget.translateHtml(div.innerHTML)
        .push(function (translated_html) {
          div.innerHTML = translated_html;

          while (container.firstChild) {
            container.removeChild(container.firstChild);
          }

          container.appendChild(div);
          return gadget.focusOnLastInput();
        });
    })

    .declareJob('focusOnLastInput', function () {
      var input_list = this.element.querySelectorAll('input');
      if (input_list.length) {
        input_list[input_list.length - 1].focus();
      }
    })

    .onEvent('submit', function () {
      var new_state = getQueryStateFromDOM(this),
        operator = new_state.operator,
        query_list = new_state.query_list,
        query,
        len = query_list.length,
        i,
        jio_query_list = [],
        options = {};

      for (i = 0; i < len; i += 1) {
        query = query_list[i];
        if (query.operator === 'keyword') {
          query.value = '%' + query.value + '%';
          query.operator = '';
        } else if (["", ">", "<", "<=", ">="].indexOf(query.operator) === -1) {
          query.operator = '';
        }

        if (query.key === PREFIX_RAW) {
          try {
            jio_query_list.push(QueryFactory.create(query.value));
          } catch (ignore) {
            // If the value can not be parsed by jio, drop it
          }
        } else {
          if (query.key.indexOf(PREFIX_COLUMN) === 0) {
            query.key = query.key.slice(PREFIX_COLUMN.length);
          } else {
            query.key = '';
          }

          jio_query_list.push(new SimpleQuery({
            key: query.key,
            operator: query.operator,
            type: "simple",
            value: query.value
          }));

        }
      }

      if (jio_query_list.length > 0) {
        options.extended_search = Query.objectToSearchText(new ComplexQuery({
          operator: operator,
          query_list: jio_query_list,
          type: "complex"
        }));
      } else {
        options.extended_search = '';
      }
      options[this.state.begin_from_key] = undefined;
      return this.redirect({
        command: 'store_and_change',
        options : options
      });

    })

    .onEvent('click', function (evt) {
      var new_state;

      if (evt.target.classList.contains('close')) {
        evt.preventDefault();
        return this.trigger();
      }

      if (evt.target.classList.contains('plus')) {
        evt.preventDefault();
        new_state = getQueryStateFromDOM(this);
        // XXX Duplicated code
        // XXX XXX Should select the first column which doesn't have a value
        new_state.query_list.push({
          key: this.state.search_column_list[0][0],
          value: ''
          // operator: 'exact_match'
        });
        return this.changeState(new_state);
      }

      if (evt.target.classList.contains('ui-icon-minus')) {
        evt.preventDefault();
        evt.target.parentElement.parentElement.removeChild(evt.target.parentElement);
      }
    }, false, false)

    .onEvent('change', function (evt) {
      if (evt.target.classList.contains('column')) {
        // Reset the operator when user change the column/key
        evt.preventDefault();
        var new_state = getQueryStateFromDOM(this),
          index = getElementIndex(evt.target.parentElement.parentElement);
        delete new_state.query_list[index].operator;
        return this.changeState(new_state);
      }
    }, false, false);

}(window, document, rJS, Handlebars,
  QueryFactory, SimpleQuery, ComplexQuery, Query));