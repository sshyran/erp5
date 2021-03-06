/*global window, rJS, jIO, FormData, UriTemplate */
/*jslint indent: 2, maxerr: 3 */
(function (window, rJS, jIO) {
  "use strict";

  // jIO call wrapper for redirection to authentication page if needed
  function wrapJioCall(gadget, method_name, argument_list) {
    var storage = gadget.state_parameter_dict.jio_storage;
    if (storage === undefined) {
      return gadget.redirect({page: "jio_configurator"});
    }
    return storage[method_name].apply(storage, argument_list)
      .push(undefined, function (error) {
        if ((error.target !== undefined) && (error.target.status === 401)) {
          var regexp,
            site,
            auth_page;
          if (gadget.state_parameter_dict.jio_storage_name === "ERP5") {
            regexp = /^X-Delegate uri=\"(http[s]?:\/\/[\/\-\[\]{}()*+=:?&.,\\\^$|#\s\w%]+)\"$/;
            auth_page = error.target.getResponseHeader('WWW-Authenticate');
            if (regexp.test(auth_page)) {
              site = UriTemplate.parse(
                regexp.exec(auth_page)[1]
              ).expand({
                came_from: window.location.href,
                cors_origin: window.location.origin,
                });
            }
          }
          if (gadget.state_parameter_dict.jio_storage_name === "DAV") {
            regexp = /^Nayookie login_url=(http[s]?:\/\/[\/\-\[\]{}()*+=:?&.,\\\^$|#\s\w%]+)$/;
            auth_page = error.target.getResponseHeader('WWW-Authenticate');
            if (regexp.test(auth_page)) {
              site = UriTemplate.parse(
                regexp.exec(auth_page)[1]
              ).expand({
                back_url: window.location.href,
                origin: window.location.origin,
                });
            }
          }
          if (site) {
            return gadget.redirect({ toExternal: true, url: site});
          }
        }
        throw error;
      });
  }

  rJS(window)

    .ready(function (gadget) {
      // Initialize the gadget local parameters
      gadget.state_parameter_dict = {};
    })

    .declareAcquiredMethod("redirect", "redirect")
    .declareAcquiredMethod("getSetting", "getSetting")
    .declareAcquiredMethod("setSetting", "setSetting")

    .declareMethod('createJio', function (jio_options) {
      var gadget = this;
      if (jio_options === undefined) {
        return;
      }
      this.state_parameter_dict.jio_storage = jIO.createJIO(jio_options);
      return this.getSetting("jio_storage_name")
        .push(function (jio_storage_name) {
          gadget.state_parameter_dict.jio_storage_name = jio_storage_name;
        });
    })
    .declareMethod('allDocs', function () {
      return wrapJioCall(this, 'allDocs', arguments);
    })
    .declareMethod('allAttachments', function () {
      return wrapJioCall(this, 'allAttachments', arguments);
    })
    .declareMethod('get', function () {
      return wrapJioCall(this, 'get', arguments);
    })
    .declareMethod('put', function () {
      return wrapJioCall(this, 'put', arguments);
    })
    .declareMethod('post', function () {
      return wrapJioCall(this, 'post', arguments);
    })
    .declareMethod('remove', function () {
      return wrapJioCall(this, 'remove', arguments);
    })
    .declareMethod('getAttachment', function () {
      return wrapJioCall(this, 'gettAttachment', arguments);
    })
    .declareMethod('putAttachment', function () {
      return wrapJioCall(this, 'putAttachment', arguments);
    })
    .declareMethod('removeAttachment', function () {
      return wrapJioCall(this, 'removeAttachment', arguments);
    })
    .declareMethod('repair', function () {
      var gadget = this;
      return this.getSetting("jio_storage_name")
        .push(function (jio_storage_name) {
          //try to specify me
          if (jio_storage_name === 'ERP5') {
            return gadget.getSetting('me')
              .push(function (me) {
                if (!me) {
                  return gadget.getSetting('jio_storage_description')
                    .push(function (configuration) {
                      gadget.state_parameter_dict.jio_storage = jIO.createJIO(configuration.remote_sub_storage);
                      return wrapJioCall(gadget, 'getAttachment', ['acl_users', configuration.remote_sub_storage.url, {format: "json"}])
                       .push(function (result) {
                         //recreate erp5 storage with indexeddb
                         me = result._links.me ? result._links.me.href : 'manager';
                         configuration.query.query += 'OR (portal_type: "Person" AND id: "' + me.split("/")[1] + '")',
                         gadget.state_parameter_dict.jio_storage = jIO.createJIO(configuration);
                         return gadget.setSetting('me', me);
                       })
                       .push(function () {
                         return gadget.setSetting('jio_storage_description', configuration);
                       });
                    });
               }
          });
         }
      })
      .push(function () {
        return wrapJioCall(gadget, 'repair', arguments);
      })
       .push(function () {
         return gadget.setSetting('last_sync_date', new Date().toLocaleString());
      });
  });

}(window, rJS, jIO));