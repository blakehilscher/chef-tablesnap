case node[:platform]
when "debian", "ubuntu"
  package "git-core"
else
  package "git"
end

git node.tablesnap.source.root do
  repository node.tablesnap.source.repository
  reference node.tablesnap.source.reference
  action :sync
end

bash "Add PPA to sources" do
  user "root"
  code %Q{
    echo "deb http://ppa.launchpad.net/synack/tablesnap/ubuntu precise main 
    deb-src http://ppa.launchpad.net/synack/tablesnap/ubuntu precise main
    " >> /etc/apt/sources.list
    apt-get update
  }
  not_if { File.readlines("/etc/apt/sources.list").grep(/synack\/tablesnap\/ubuntu/).any? }
end

package "daemon" do
  action :install
  options("--force-yes")
end

package "tablesnap" do
  action :install
  options("--force-yes")
end

template "/etc/default/tablesnap" do
  source "default.erb"
  owner 'root'
  group 'root'
  mode  0644
end

template "/etc/init.d/tablesnap" do
  source "init.erb"
  owner 'root'
  group 'root'
  mode  0755
end

directory node.tablesnap.source.root do
  owner 'root'
  group 'root'
  mode 0644
  action :create
end

template '/usr/bin/tablerestore' do
  source "tablerestore.erb"
  owner 'root'
  group 'root'
  mode  0755
end

template '/usr/bin/tabletruncate' do
  source "tabletruncate.erb"
  owner 'root'
  group 'root'
  mode  0755
end

template '/usr/bin/tableslurp' do
  source "tableslurp.py"
  owner 'root'
  group 'root'
  mode  0755
end

directory node.tablesnap.logdir do
  owner 'root'
  group 'root'
  mode 0644
  action :create
end

bash "link tablechop" do
  user "root"
  code "ln -sf #{node.tablesnap.source.root}/tablechop /usr/bin/tablechop"
end

bash "executable tablechop" do
  user "root"
  code "chmod +x /usr/bin/tablechop"
end

bash "Ensure logfile is present" do
  user "root"
  code "touch #{node.tablesnap.logdir}/tablesnap.log"
end

bash "Restart" do
  user "root"
  code %{
    /etc/init.d/tablesnap stop
    /etc/init.d/tablesnap start
  }
end
