# Jumpbox Files

## instrumentationbrowser_0.0.2-172_amd64.deb

The Instrumentation Browser deb package that we're currently using.

## instrumentationbrowser_0.4.8_amd64.deb

The Instrumentation Browser deb package that we'll need to use if the jumpbox is recreated using
Ubuntu Bionic. To use a different package, update the instrumentation_browser_file_name variable
at the beginning of packages.yml. This will change what version of Instrumentation Browser gets
installed when the jumpbox_packages Jenkins job runs.

You can download the latest package for a given distro at
https://wiki.viasat.com/display/Proj/InstrumentationBrowser.

## databus_linux_amd64

The package that installs databus-cli.
