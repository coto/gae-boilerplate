[Google App Engine Boilerplate](http://appengine.beecoss.com) [![Build Status](https://secure.travis-ci.org/coto/gae-boilerplate.png)](http://travis-ci.org/coto/gae-boilerplate)
==============================

Sponsored by <a href="http://www.jetbrains.com/pycharm/" alt="Download PyCharm">
  <img src="http://www.jetbrains.com/img/logos/pycharm_logo142x29.gif">
</a>

Google App Engine Boilerplate gets your project off the ground quickly using the Google App Engine platform. 
Create powerful applications by using the latest technology supported on Google App Engine. 
It will introduces new developers to App Engine and advanced developers to follow best practices.

[Try a online demo](http://appengine.beecoss.com)

What's a Boilerplate?
---------------------
A Boilerplate is used to describe sections of code that can be reused over and over in new contexts or applications which provides good default values, reducing the need to specify program details in every project. ([wikipedia](http://en.wikipedia.org/wiki/Boilerplate_code))

What makes this Boilerplate Amazing?
------------------------------------
It is fully featured, actively maintained, and uses the latest and most supported technologies of Google App Engine.

New to Google App Engine? Learn about it by watching [this video](http://www.youtube.com/watch?v=bfgO-LXGpTM) of @bslatkin or reading [the official documentation](https://developers.google.com/appengine/).

Get started in just a few easy steps
------------------------------------
1. Download the last version of the [App Engine SDK](http://code.google.com/appengine/downloads.html#Google_App_Engine_SDK_for_Python) for Linux, Mac OS or Windows.
1. Download or clone the code of this Boilerplate ([here](https://github.com/coto/gae-boilerplate/zipball/master))
1. Run locally ([instructions](https://developers.google.com/appengine/docs/python/tools/devserver)).
1. Set your 'application' name in [app.yaml](https://github.com/coto/gae-boilerplate/blob/master/app.yaml)
1. Set custom config parameters in bp_content/themes [config/localhost.py](https://github.com/coto/gae-boilerplate/blob/master/bp_content/themes/default/config/localhost.py), [config/testing.py](https://github.com/coto/gae-boilerplate/blob/master/bp_content/themes/default/config/testing.py) and [config/production.py](https://github.com/coto/gae-boilerplate/blob/master/bp_content/themes/default/config/production.py) like secret key, [recaptcha code](http://www.google.com/recaptcha/whyrecaptcha), salt and other.
 * Boilerplate will identify which config file to use in local, unit testing and production.
 * To get started, look the default settings in [bp_includes/config.py](https://github.com/coto/gae-boilerplate/blob/master/bp_includes/config.py). Those settings will be overwrite for your config files.
 * Most of the default settings will need to be changed to yield a secure and working application.
1. Set Authentication Options dropdown to Federated Login in the Google App Engine control panel (or if you do not want federated login, set enable_federated_login to false in config.py)
1. Deploy it online ([instructions](https://developers.google.com/appengine/docs/python/gettingstarted/uploading) - recommended setup: python 2.7, high replication datastore)

Please note that your custom application code **should be located in the bp_content folder within your own theme**.
The intention is that separating the boilerplate code from your application code will avoid merge conflicts as you keep up with future boilerplate changes.

Functions and features
----------------------
+ Authentication (Sign In, Sign Out, Sign Up)
+ Federated Login - login via your favorite social network (Google, Twitter, etc...) powered by OpenID and OAuth
+ Reset Password
+ Update User Profile
+ Contact Form
+ Client side and server side form validation
+ Automatic detection of user language
+ Support for many Languages (English, Spanish, Italian, French, Chinese, Indonesian, German, Russian, etc)
+ Visitors Log
+ Notifications and Confirmation for users when they change their email or password
+ Responsive Design for viewing on PCs, tablets, and mobile phones (synchronized with Twitter-Bootstrap project)
+ Mobile identification
+ Unit Testing
+ Error handling
+ Basic user management features available under /admin/users/ for Google Application Administrators


Resources
---------
Boilerplate has a Google group ([gae-boilerplate](https://groups.google.com/forum/?fromgroups#!forum/gae-boilerplate)) for discussions and a Twitter account ([@gaeboilerplate](http://twitter.com/gaeboilerplate/)) for sharing related resources.

Open Source
-----------
If you want to add, fix or improve something, create an [issue](https://github.com/coto/gae-boilerplate/issues) or send a [Pull Request](https://github.com/coto/gae-boilerplate/pull/new/master).

Before committing fixes we recommend running the unitests (in the boilerplate package).  This will help guard against changes that accidently break other code.  See the testing section below for instructions.

Feel free to commit improvements or new features. Feedback, comments and ideas are welcome.

Run
---
+ You can run this project directly from terminal with Fabric.

    ```bash
    fab start
    ```
+ Also you can run it clearing datastore.

    ```bash
    fab start:clear
    ```

Unit Testing
------------
**Requirements**
+ Install pip with [distribute](http://packages.python.org/distribute/) in order to install next packages.
+ Before running unittests it is necessary to install [webtest](http://webtest.pythonpaste.org/en/latest/index.html#installation), [mock](http://www.voidspace.org.uk/python/mock/), and [pyquery](http://packages.python.org/pyquery/) in your local python installation.

  ```bash
    sudo pip install webtest
    sudo pip install mock
    sudo pip install pyquery
  ```
+ The best way to run unittests is though Fabric.

  ```bash
    sudo pip install Fabric
  ```

**Running Unit Tests**
+ To run unittests with Fabric run  `fab test` command in terminal.
+ Also Unit tests can be run via [testrunner](https://github.com/coto/gae-boilerplate/blob/master/testrunner.py) or in Eclipse by right clicking on the web folder and selecting "run as..." -> "Python unit-test".
+ You may need to add /boilerplate/external to your python path.

**Adding yours Unit Test**
+ Please add unittests for your application to your handler folder in a **test.py** file.
+ Your own unittests can be created similarly to those in the boilerplate.  Inheriting from boilerplate.lib.test_helpers.HandlerHelpers will provide access to convenient handler testing methods used by the boilerplate.


Deploy
------
+ To deploy your project with Fabric, just run this command in Terminal.

    ```bash
    fab deploy
    ```
+ Remember to change **application**, **version**, **theme** in app.yaml according to your project.

Technologies used
-----------------
+ Python 2.7.5
+ [NDB 1.0.10](http://developers.google.com/appengine/docs/python/ndb/) (The best datastore API for the Google App Engine Python runtime).
+ [Jinja2 2.6](http://jinja.pocoo.org/docs/) (A fully featured template engine for Python).
+ [WTForms-1.0.2](http://wtforms.simplecodes.com/) (Forms validation framework keeping user interaction secure and flexible with or without javascript).
+ [Babel-0.9.6](http://babel.edgewall.org/) and [gaepytz-2011h](http://code.google.com/p/gae-pytz/) (Industy standard internationalization renders the site in multiple languages).
+ [webapp2 2.5.2](http://webapp-improved.appspot.com/) (A lightweight Python web framework, the most compatible with Google App Engine).
    + webapp2_extras.sessions
    + webapp2_extras.routes
    + webapp2_extras.auth
    + webapp2_extras.i18n
+ Code written following the [Google Python Style Guide](http://google-styleguide.googlecode.com/svn/trunk/pyguide.html)
+ Unit testing with [unittest](http://docs.python.org/library/unittest.html), [webtest](http://webtest.pythonpaste.org/en/latest/index.html), [pyquery](http://packages.python.org/pyquery/)
+ OpenID library provided by Google App Engine
+ OAuth2 for federated login providers that do not support OpenID

Front-end Technologies
----------------------
+ [HTML5Boilerplate](http://html5boilerplate.com/)
+ [Modernizr 2.6.1](http://modernizr.com)
+ [jQuery 1.8.2](http://jquery.com)
+ [Twitter Bootstrap 3.1.1](http://twitter.github.com/bootstrap/) upgraded from 2.2.1. Template for Desktop Version.

Help to translate to new languages or improve old translations
--------------------------------------------------------------
In each locale/<locale code>/LC_MESSAGES directory there is a file messages.po. Please help us translate the text in these files.
msgid is the text in English.  msgstr is the translation to the language indicated by the locale code.  For example:

<tt>msgid "Change your password"</tt>

<tt>msgstr "Cambiar tu contraseña"</tt>

**Requirements**
+ Install before pip with distribute_setup.py (Read the environment setup document)

    ```bash
    sudo pip install babel
    sudo pip install jinja2
    ```

**Translating**
+ To execute the translation, run these two commands. (before the second one, go to locale folder to include your translation)

    ```bash
    fab lang
    fab lang:compile
    ```

Working with Internationalization (i18n)
----------------------------------------
This boilerplate comes bundled with babel, pytz, and automatic language detection which together provide powerful internationalization capability.
Text to be translated needs to be indicated in code and then translated by users like you after which it is compiled for speed.

Adding or updating text to be translated or adding new languages requires more work as indicated in the steps below:

1. Text to be translated should be enclosed in `_("text to translate")` in *.py files.
   + `{{..._("text to translate")...}}`
   + `{%..._("text to translate")...%}`
1. In html templates translated text is indicated by:
   + `{% trans %}text to translate{% endtrans %}`
   
   **NOTE:** Translations can be added to other types of files too.  See [babel.cfg](https://github.com/coto/gae-boilerplate/blob/master/locale/babel.cfg)
   and [babel.cfg documentation](http://babel.edgewall.org/wiki/Documentation/0.9/messages.html)
1. Obtain pybabel to perform the steps below.  You will need to install and compile [jinja2](http://jinja.pocoo.org/docs/) and [babel](http://babel.edgewall.org/wiki/Download).
   Note that you may need to first install [setuptools and easy_install](http://pypi.python.org/pypi/setuptools).
   pybabel.exe can be run from the Scripts directory in your python installation.
   * `easy_install jinja2 babel`
1. Babel then needs to find all translationed text blocks throughout code and templates.
   After installing pybabl run this command to extract messages (assuming ./ is the location of this boilerplate):
   <tt>pybabel extract -F ./locale/babel.cfg -o ./locale/messages.pot ./ --sort-output --no-location --omit-header</tt>
1. Update translations of existing languages or add new languages
   1. Update translations of existing languages by running this command for each locale:
      <tt>pybabel update -l es_ES -d ./locale -i ./locale/messages.pot --previous --ignore-obsolete</tt>
      Run this command for each locale by replacing es_ES in the command.  Locale names are the directory names in ./locale.
   1. Add new languages:
      Run this command for each new language to add.  You will need to replace es_ES in the command with the locale code to add:
      <tt>pybabel init -l es_ES -d ./locale -i ./locale/messages.pot</tt>
      Add the locale to the locales array in your themes/*<your_theme>*/config/.
      Instructions on how to pick a locale code are provided in the comments above the array.
1. Provide translations for each language
   In each locale/<locale code>/LC_MESSAGES directory there is a file messages.po.  Users translate the strings in these files.
   msgid is the text in English.  msgstr is the translation to the language indicated by the locale code.  For example:
   + `msgid "Change your password"`
   + `msgstr "Cambiar tu contraseña"`
1. Compile translations
   Run: <tt>pybabel compile -f -d ./locale</tt>

See [webapp2's tutorial](http://webapp-improved.appspot.com/tutorials/i18n.html) and [pybabel's docs](http://babel.edgewall.org/wiki/Documentation/cmdline.html) for more details.

**Disabling i18n**

i18n can be disabled and language options hidden.  Set locales in config.py to None or empty array [] to do this.  This may be useful to provide a performance boost or simplify sites that serve a market with only one language.
The locale directory can be safely removed to save space if not needed but the babel and pytz directories cannot be removed without breaking code (imports and trans statements) at this time.

Security
--------
**SSL**
+ SSL is enabled site wide by adding <tt>secure: always</tt> to the section: <tt>- url: /.*</tt> in app.yaml (remove this line to disable)
+ SSL either requires a free google app engine *.appspot.com domain or a [custom domain and certificate](https://developers.google.com/appengine/docs/ssl)
+ Alternatively SSL can be enabled at a controller level via webapp2 schemes. Use the secure_scheme provided in routes.py
+ It is recommended to enable ssl site wide to help prevent [session hijacking](http://en.wikipedia.org/wiki/Session_hijacking)

**Passwords**
+ Passwords are hashed and encrypted with SHA512 and PyCrypto.

**CSRF**
+ [Cross-site request forgery](http://en.wikipedia.org/wiki/Cross-site_request_forgery) protection

Acknowledgements
----------------
Google App Engine Boilerplate is a collaborative project created by [coto](https://github.com/coto) which is bringing to you thanks to the help of
these [amazing people](https://github.com/coto/gae-boilerplate/graphs/contributors?type=a)

**Top 10: Primary contributors:**
+ [Tmeryu](https://github.com/tmeryu)
+ [Peta15](https://github.com/peta15)
+ [Sergue1](https://github.com/sergue1)
+ [Sabirmostofa](https://github.com/sabirmostofa)
+ [Pmanacas](https://github.com/pmanacas)
+ [copycat91](https://github.com/copycat91)
+ [Mooose](https://github.com/mooose)
+ [f1shear](https://github.com/f1shear)
+ [presveva](https://github.com/presveva)
+ [Sorced-Jim](https://github.com/sorced-Jim)
