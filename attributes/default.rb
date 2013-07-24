default[:tablesnap][:use_node_name] = false         # Use the node.name as --name ?

default[:tablesnap][:source][:repository] = "git@github.com:synack/tablesnap.git"
default[:tablesnap][:source][:root] = "/etc/tablesnap"
default[:tablesnap][:source][:reference] = "master"

default[:tablesnap][:logdir] = "/var/log/tablesnap"
default[:tablesnap][:aws_key] = ""
default[:tablesnap][:aws_secret] = ""
default[:tablesnap][:s3_bucket] = "cassandra-archive"
default[:tablesnap][:data_dir] = "/var/lib/cassandra/data/"


default[:tablesnap][:recursive] = true              # Recursively watch the given path(s)s for new SSTables
default[:tablesnap][:auto_add] = false              # Automatically start watching new subdirectories within path(s)
default[:tablesnap][:backup] = true                 # Backup existing files to S3 if they are not already there
default[:tablesnap][:prefix] = ''                   # Set a string prefix for uploaded files in S3
default[:tablesnap][:without_index] = false         # Do not store a JSON representation of the current directory listing in S3 when uploading a file to S3.
default[:tablesnap][:threads] = 4                   # Number of writer threads
default[:tablesnap][:name] = false                  # Use this name instead of the FQDN to identify the files from this host
default[:tablesnap][:exclude] = ''                  # Exclude files matching this regular expression.
default[:tablesnap][:include] = ''                  # Include files matching this regular expression.
default[:tablesnap][:max_upload_size] = 5120        # Max size for files to be uploaded before doing multipart
default[:tablesnap][:multipart_chunk_size] = 256    # Chunk size for multipart uploads (default: 256M or 10% of free memory if default is not available)

default[:tableslurp][:owner] = 'cassandra'
default[:tableslurp][:group] = 'cassandra'