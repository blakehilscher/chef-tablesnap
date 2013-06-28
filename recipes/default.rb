bash "Add PPA to sources" do
  user "root"
  code %Q{
    echo "deb http://ppa.launchpad.net/synack/tablesnap/ubuntu precise main 
    deb-src http://ppa.launchpad.net/synack/tablesnap/ubuntu precise main
    " >> /etc/apt/sources.list
    apt-get update
  }
end

bash "Add PPA to sources" do
  user "root"
  code %Q{
    echo "deb http://ppa.launchpad.net/synack/tablesnap/ubuntu precise main 
    deb-src http://ppa.launchpad.net/synack/tablesnap/ubuntu precise main
    " >> /etc/apt/sources.list
    apt-get update
  }
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

directory node.tablesnap.logdir do
  owner 'root'
  group 'root'
  mode 0644
  action :create
end

bash "Ensure logfile is present" do
  user "root"
  code "touch #{node.tablesnap.logdir}/tablesnap.log"
end

package "tablesnap" do
  action :install
  options("--force-yes")
end

bash "Restart" do
  user "root"
  code %{
    /etc/init.d/tablesnap stop
    /etc/init.d/tablesnap start
  }
end
