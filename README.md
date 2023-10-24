# CloudWatchExporter

Python script that allows you to launch a docker container, 
execute a bash script and import its logs into AWSCloudWatch


Usage:

```
python main.py 
  --docker-image <image-name> 
  --bash-command $'echo 1' 
  --aws-cloudwatch-group <group-name>
  --aws-cloudwatch-stream <stream-name>
  --aws-access-key-id <key> 
  --aws-secret-access-key <key>
  --aws-region us-east-1
```