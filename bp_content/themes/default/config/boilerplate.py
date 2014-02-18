config = {

    # This config file is used only in appengine.beecoss.com (Sample website)
    # Don't use values defined here
    'environment': "boilerplate",

    # contact page email settings
    'contact_sender': "appengine@beecoss.com",
    'contact_recipient': "appengine@beecoss.com",

    'captcha_public_key': "6Ldi0u4SAAAAAC8pjDop1aDdmeiVrUOU2M4i23tT",
    'captcha_private_key': "6Ldi0u4SAAAAAPzk1gaFDRQgry7XW4VBvNCqCHuJ",

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
        """,
    'twitter_consumer_key': 'rrgGr00w3HRJYzmxNLMgzQ',
    'twitter_consumer_secret': '5IdJDvSRdbkETeFjFeIxS7IoERWn8nGk5NfGSGG9ynk',

    'fb_api_key': '265551733563729',
    'fb_secret': '9de58570269f23b768726f3617ceb6ce',

# ----> ADD MORE CONFIGURATION OPTIONS HERE <----

}