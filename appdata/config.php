<?php

define('LOG_DRIVER', 'stdout');
define('DEBUG', false);
define('KANBOARD_URL', "http://localhost:5000/kanboard/");
define('PLUGIN_INSTALLER', true);

define('ENABLE_URL_REWRITE', true);
// Enable/disable reverse proxy authentication
define('REVERSE_PROXY_AUTH', true); // Set this value to true

// The HTTP header to retrieve. If not specified, REMOTE_USER is the default
define('REVERSE_PROXY_USER_HEADER', 'HTTP_REMOTE_USER');

// The default Kanboard admin for your organization.
// Since everything should be filtered by the reverse proxy,
// you should want to have a bootstrap admin user.
define('REVERSE_PROXY_DEFAULT_ADMIN', 'admin@signin.chopshoplib.info');

// Header name to use for the user email (optional)
define('REVERSE_PROXY_EMAIL_HEADER', 'HTTP_REMOTE_EMAIL');

// Header name to use for the user full name (optional)
define('REVERSE_PROXY_FULLNAME_HEADER', 'HTTP_REMOTE_NAME');