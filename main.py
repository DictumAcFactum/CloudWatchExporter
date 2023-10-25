import time
import boto3
import docker
import argparse

from typing import Protocol, Sequence, Optional
from docker.models.containers import Container


EXPORT_LOGS_BATCH_SIZE = 100


class AWSResource(Protocol):
    ...


class AWSCloudWatch(AWSResource):
    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        region: str,
        group: str,
        stream: str,
        batch_size: Optional[int] = None,
    ):
        self.client = boto3.client(
            "logs",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )
        self.group = group
        self.stream = stream
        self.batch_size = batch_size or EXPORT_LOGS_BATCH_SIZE

    def create_log_group(self) -> None:
        try:
            self.client.create_log_group(logGroupName=self.group)
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass

    def create_log_stream(self) -> None:
        try:
            self.client.create_log_stream(logGroupName=self.group, logStreamName=self.stream)
        except self.client.exceptions.ResourceAlreadyExistsException:
            pass

    def send_logs(self, logs: Sequence[str]) -> None:
        self.client.put_log_events(
            logGroupName=self.group,
            logStreamName=self.stream,
            logEvents=[{"timestamp": int(time.time() * 1000), "message": log} for log in logs],
        )

    def monitor_container_logs(self, container: Container) -> None:
        logs = []
        for log in container.logs(stream=True, follow=True):
            logs.append(log.decode().strip())
            if len(logs) >= self.batch_size:
                self.send_logs(logs=logs)
                logs.clear()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker-image", required=True)
    parser.add_argument("--bash-command", required=True)
    parser.add_argument("--aws-cloudwatch-group", required=True)
    parser.add_argument("--aws-cloudwatch-stream", required=True)
    parser.add_argument("--aws-access-key-id", required=True)
    parser.add_argument("--aws-secret-access-key", required=True)
    parser.add_argument("--aws-region", required=True)

    args = parser.parse_args()

    aws_cloud_watch = AWSCloudWatch(
        access_key_id=args.aws_access_key_id,
        secret_access_key=args.aws_secret_access_key,
        region=args.aws_region,
        group=args.aws_cloudwatch_group,
        stream=args.aws_cloudwatch_stream,
    )

    # Create AWS CloudWatch log group and stream if not exists
    aws_cloud_watch.create_log_group()
    aws_cloud_watch.create_log_stream()

    # Run the Docker container with the provided bash command
    container: Container = docker.from_env().containers.run(
        image=args.docker_image, command=args.bash_command, detach=True
    )

    try:
        aws_cloud_watch.monitor_container_logs(container)
    except KeyboardInterrupt:
        print(f"Monitoring container {container.name} stopped.")
    except Exception as e:
        container.stop()
        container.remove()
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
