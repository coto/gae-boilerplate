config = {

# This config file is used only in appengine.beecoss.com (Sample website)
# Don't use values defined here
'environment': "boilerplate",

# contact page email settings
'contact_sender': "appengine@beecoss.com",
'contact_recipient': "appengine@beecoss.com",

'captcha_public_key': "6Lednu0SAAAAAKPyxzxIljKc3po4Fz7lmLsn5s3T",
'captcha_private_key': "6Lednu0SAAAAAGkiiVKmkLvpGT1a-sCkaKf-E4xb",

'send_mail_developer': True,

# fellas' list
'developers': (
    ('GAE Developer', 'gae-developer2014@beecoss.com'),
),

# It is just an example to fill out this value
'google_analytics_code': """
        <script>
        (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
        (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
        m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
        })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

        ga('create', 'UA-47489500-1', 'auto', {'allowLinker': true});
        ga('require', 'linker');
        ga('linker:autoLink', ['beecoss.com', 'blog.beecoss.com', 'appengine.beecoss.com']);
        ga('send', 'pageview');
        </script>
    """

# ----> ADD MORE CONFIGURATION OPTIONS HERE <----

}