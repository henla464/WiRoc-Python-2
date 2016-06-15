/* (function ($) {
     $.widget("custom.combobox", {
         _create: function (a) {
             this.wrapper = $("<span>")
          .addClass("custom-combobox")
          .insertAfter(this.element);

             this.element.hide();
             this._createAutocomplete();
             this._createShowAllButton();
         },
         appendTo: function (jqueryStr) {
           this.input.autocomplete("option", "appendTo", jqueryStr);  
         },
         _createAutocomplete: function () {
             var selected = this.element.children(":selected"),
          value = selected.val() ? selected.text() : "";

             this.input = $("<input>")
          .appendTo(this.wrapper)
          .val(value)
          .attr("title", "")
          .addClass("custom-combobox-input ui-widget ui-widget-content ui-state-default ui-corner-left")
          .autocomplete({
              delay: 0,
              minLength: 0,
              source: $.proxy(this, "_source")
          })
          .tooltip({
              tooltipClass: "ui-state-highlight"
          });

             this._on(this.input, {
                 autocompleteselect: function (event, ui) {
                     ui.item.option.selected = true;
                     this._trigger("select", event, {
                         item: ui.item.option
                     });
                 },

                 autocompletechange: "_removeIfInvalid"
             });
         },

         _createShowAllButton: function () {
             var input = this.input,
          wasOpen = false;

             $("<a>")
          .attr("tabIndex", -1)
          .attr("title", "Show All Items")
          .tooltip()
          .appendTo(this.wrapper)
          .button({
              icons: {
                  primary: "ui-icon-triangle-1-s"
              },
              text: false
          })
          .removeClass("ui-corner-all")
          .addClass("custom-combobox-toggle ui-corner-right")
          .mousedown(function () {
              wasOpen = input.autocomplete("widget").is(":visible");
          })
          .click(function () {
              input.focus();

              // Close if already visible
              if (wasOpen) {
                  return;
              }

              // Pass empty string as value to search for, displaying all results
              input.autocomplete("search", "");
          });
         },

         _source: function (request, response) {
             var matcher = new RegExp($.ui.autocomplete.escapeRegex(request.term), "i");
             response(this.element.children("option").map(function () {
                 var text = $(this).text();
                 if (this.value && (!request.term || matcher.test(text)))
                     return {
                         label: text,
                         value: text,
                         option: this
                     };
             }));
         },

         _removeIfInvalid: function (event, ui) {

             // Selected an item, nothing to do
             if (ui.item) {
                 return;
             }

             // Search for a match (case-insensitive)
             var value = this.input.val(),
          valueLowerCase = value.toLowerCase(),
          valid = false;
             this.element.children("option").each(function () {
                 if ($(this).text().toLowerCase() === valueLowerCase) {
                     this.selected = valid = true;
                     return false;
                 }
             });

             // Found a match, nothing to do
             if (valid) {
                 return;
             }

             // Remove invalid value
             this.input
          .val("")
          .attr("title", value + " didn't match any item")
          .tooltip("open");
             this.element.val("");
             this._delay(function () {
                 this.input.tooltip("close").attr("title", "");
             }, 2500);
             this.input.data("ui-autocomplete").term = "";
         },
         autocomplete: function (value) {
             this.element.val(value);
             var text = this.element.children("option[value='" + value + "']").text();
             this.input.val(text);
         },
         _destroy: function () {
             this.wrapper.remove();
             this.element.show();
         }
     });
 })(jQuery);
 */

 /*
 * Combobox widget. This widget extends the jQuery UI autocomplete widget. 
 *  
 * usage:  $("#select_element").combox();
 *         $("#input_element").combox( {minLength: 2, delay: 200, source: anArray} );
 *  
 * For select elements, the source list is automatically generated from the option elements.
 * 
 * To configure a label decorator (i.e. "[admin]"), set the decoratorField when you 
 * initialize the combobox. The field corresponds to the object field, if the source is
 * an array of objects. Or it's the attribute in <option> if the source is a select drop-down menu. 
 */

 (function ($) {
     $.widget("ui.combobox", $.ui.autocomplete,
    	{
    	    options: {
    	        /* override default values here */
    	        minLength: 2,
    	        /* the argument to pass to ajax to get the complete list */
    	        ajaxGetAll: { get: "all" },
    	        /* you can specify the field to use as a label decorator, 
    	        * it's appended to the end of the label and is excluded 
    	        * from pattern matching.    
    	        */
    	        decoratorField: null,
    	        appendTo: "body"
    	    },

    	    _create: function () {
    	        if (this.element.is("SELECT")) {
    	            this._selectInit();
    	            return;
    	        }

    	        $.ui.autocomplete.prototype._create.call(this);

    	        var input = this.element;
    	       

    	        input.addClass("ui-widget ui-widget-content ui-corner-left")
    			     .click(function () { this.select(); });

    	        this.button = $("<button type='button'>&nbsp;</button>")
                .attr("tabIndex", -1)
                .attr("title", "Show All Items")
                .insertAfter(input)
                .button({
                    disabled: true, // to be enabled when the menu is ready.
                    icons: { primary: "ui-icon-triangle-1-s" },
                    text: false
                })
                .removeClass("ui-corner-all")
                .addClass("ui-corner-right ui-button-icon")
                .click(function (event) {
                    // when user clicks the show all button, we display the cached full menu
                    var data = input.data("ui-combobox");
                    clearTimeout(data.closing);
                    if (!input.isFullMenu) {
                        data._swapMenu();
                    }
                    /* input/select that are initially hidden (display=none, i.e. second level menus), 
                    will not have position cordinates until they are visible. */
                    input.combobox("widget").css("display", "block")
                    .position($.extend({ of: input },
                    	data.options.position
                    	));
                    input.focus();
                    data._trigger("open");
                    // containers such as jquery-ui dialog box will adjust it's zIndex to overlay above other elements.
                    // this becomes a problem if the combobox is inside of a dialog box, the full drop down will show
                    // under the dialog box.
                    //if (input.combobox("widget").zIndex() <= input.parent().zIndex()) {
                    //    input.combobox("widget").zIndex(input.parent().zIndex() + 1);
                    //}
                });

    	        /* to better handle large lists, put in a queue and process sequentially */
    	        $(document).queue(function () {
    	            var data = input.data("ui-combobox");
    	            if ($.isArray(data.options.source)) {
    	                $.ui.combobox.prototype._renderFullMenu.call(data, data.options.source);
    	            } else if (typeof data.options.source === "string") {
    	                $.getJSON(data.options.source, data.options.ajaxGetAll, function (source) {
    	                    $.ui.combobox.prototype._renderFullMenu.call(data, source);
    	                });
    	            } else {
    	                $.ui.combobox.prototype._renderFullMenu.call(data, data.source());
    	            }
    	        });
    	    },

    	    /* initialize the full list of items, this menu will be reused whenever the user clicks the show all button */
    	    _renderFullMenu: function (source) {
    	        var self = this,
    			    input = this.element,
                    ul = input.data("ui-combobox").menu.element,
                    lis = [];
    	        source = this._normalize(source);
    	        input.data("ui-combobox").menuAll = input.data("ui-combobox").menu.element.clone(true).appendTo("body")[0];
    	        for (var i = 0; i < source.length; i++) {
    	            var item = source[i],
                	    label = item.label;
    	            if (this.options.decoratorField != null) {
    	                var d = item[this.options.decoratorField] || (item.option && $(item.option).attr(this.options.decoratorField));
    	                if (d != undefined)
    	                    label = label + " " + d;
    	            }
    	            lis[i] = "<li class=\"ui-menu-item\" role=\"menuitem\"><a class=\"ui-corner-all\" tabindex=\"-1\">" + label + "</a></li>";
    	        }
    	        ul[0].innerHTML = lis.join("");
    	        this._resizeMenu();

    	        var items = $("li", ul).on("mouseover", "mouseout", function (event) {
    	            if (event.type == "mouseover") {
    	                self.menu.focus(event, $(this));
    	            } else {
    	                self.menu.blur();
    	            }
    	        });
    	        for (var i = 0; i < items.length; i++) {
    	            $(items[i]).data("ui-autocomplete-item", source[i]);
    	        }
    	        input.isFullMenu = true;
    	        this._swapMenu();
    	        // full menu has been rendered, now we can enable the show all button.
    	        self.button.button("enable");
    	        setTimeout(function () {
    	            $(document).dequeue();
    	        }, 0);
    	    },

    	    /* overwrite. make the matching string bold and added label decorator */
    	    _renderItem: function (ul, item) {
    	        var label = item.label.replace(new RegExp(
                	"(?![^&;]+;)(?!<[^<>]*)(" + $.ui.autocomplete.escapeRegex(this.term) +
                    ")(?![^<>]*>)(?![^&;]+;)", "gi"), "<strong>$1</strong>");
    	        if (this.options.decoratorField != null) {
    	            var d = item[this.options.decoratorField] || (item.option && $(item.option).attr(this.options.decoratorField));
    	            if (d != undefined) {
    	                label = label + " " + d;
    	            }
    	        }
    	        return $("<li></li>")
                    .data("ui-autocomplete-item", item)
                    .append("<a>" + label + "</a>")
                    .appendTo(ul);
    	    },

    	    close: function () {
    	        if (this.element.isFullMenu) {
    	            this._swapMenu();
    	        }
    	        // super()
    	        $.ui.autocomplete.prototype.close.call(this);
    	    },

    	    /* overwrite. to cleanup additional stuff that was added */
    	    destroy: function () {
    	        if (this.element.is("SELECT")) {
    	            this.input.removeData("ui-combobox", "menuAll");
    	            this.input.remove();
    	            this.element.removeData().show();
    	            return;
    	        }
    	        // super()
    	        $.ui.autocomplete.prototype.destroy.call(this);
    	        // clean up new stuff
    	        this.element.removeClass("ui-widget ui-widget-content ui-corner-left");
    	        this.button.remove();
    	    },

    	    /* overwrite. to swap out and preserve the full menu */
    	    search: function (value, event) {
    	        var input = this.element;
    	        if (input.isFullMenu) {
    	            this._swapMenu();
    	        }
    	        // super()
    	        $.ui.autocomplete.prototype.search.call(this, value, event);
    	    },
    	    autocomplete: function (value) {
    	        this.element.val(value);
    	        var text = this.element.children("option[value='" + value + "']").text();
    	        this.input.val(text);
    	    },
    	    _change: function (event) {
    	        if (!this.selectedItem) {
    	            var matcher = new RegExp("^" + $.ui.autocomplete.escapeRegex(this.element.val()) + "$", "i"),
                        match = $.grep(this.options.source, function (value) {
                            return matcher.test(value.label);
                        });
    	            if (match.length) {
    	                if (match[0].option != undefined) match[0].option.selected = true;
    	            } else {
    	                // remove invalid value, as it didn't match anything
    	                if (this.options.selectElement) {
    	                    var firstItem = this.options.selectElement.children("option:first");
    	                    this.element.val(firstItem.text());
    	                    firstItem.prop("selected", true);
    	                } else {
    	                    this.element.val("");
    	                }
    	                $(event.target).data("ui-combobox").previous = null;  // this will force a change event
    	            }
    	        }
    	        // super()
    	        $.ui.autocomplete.prototype._change.call(this, event);
    	    },

    	    _swapMenu: function () {
    	        var input = this.element,
            	    data = input.data("ui-combobox"),
            	    tmp = data.menuAll;
    	        data.menuAll = data.menu.element.hide()[0];
    	        data.menu.element[0] = tmp;
    	        input.isFullMenu = !input.isFullMenu;
    	    },

    	    /* build the source array from the options of the select element */
    	    _selectInit: function () {
    	        var select = this.element,
                    selectClass = select.attr("class"),
                    selectStyle = select.attr("style"),
                    selected = select.children(":selected"),
                    value = $.trim(selected.text());
    	        select.hide();
    	        this.options.source = select.children("option").map(function () {
    	            return { label: $.trim(this.text), option: this };
    	        }).toArray();
    	        var userSelectCallback = this.options.select;
    	        var userSelectedCallback = this.options.selected;
    	        this.options.select = function (event, ui) {
    	            ui.item.option.selected = true;
    	            select.change();
    	            if (userSelectCallback) userSelectCallback(event, ui);
    	            // compatibility with jQuery UI's combobox.
    	            if (userSelectedCallback) userSelectedCallback(event, ui);
    	        };
    	        this.options.selectElement = select;
    	        this.input = $("<input>").insertAfter(select).val(value);
    	        if (selectStyle) {
    	            this.input.attr("style", selectStyle);
    	        }
    	        if (selectClass) {
    	            this.input.attr("class", selectClass);
    	        }
    	        this.input.combobox(this.options);
    	    },
    	    inputbox: function () {
    	        if (this.element.is("SELECT")) {
    	            return this.input;
    	        } else {
    	            return this.element;
    	        }
    	    }
    	}
    );
 })(jQuery);