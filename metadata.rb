maintainer       "Blake"
maintainer_email "blake@hilscher.ca"
license          "Apache 2.0"
description      "Installs tablesnap on debian/ubuntu from ppa package"
long_description IO.read(File.join(File.dirname(__FILE__), 'README.md'))
version          "0.6.1"

depends "build-essential"
depends "git"

supports "ubuntu"