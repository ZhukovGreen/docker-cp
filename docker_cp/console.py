import logging
import pathlib
import sys
import tarfile
from io import BytesIO

import click
import docker

logger = logging.getLogger(__name__)
client = docker.from_env()


@click.command()
@click.option(
    "-b",
    "--buffer-length",
    "buffer_length",
    default=1,
    help="Buffer size",
    show_default=True,
    type=int,
)
@click.option("-v", "--verbose", count=True, help="Verbosity of the tool")
@click.argument("src", type=str)
@click.argument("target", type=str)
def main(buffer_length, verbose, src, target):
    """Simple docker cp implementation.

    Copying files from SRC to TARGET. Path for a container defined like:
    {container_name}:{container_path}

    Examples:\n
        * docker-cp test:/etc/fedora-release .\n
        * docker-cp ./pyproject.toml test/tmp/
    """
    try:
        assert buffer_length > 0
    except AssertionError:
        raise click.BadParameter("Buffer length should be bigger than 0")
    logging.basicConfig(
        stream=sys.stderr, level=logging.DEBUG if verbose else logging.INFO
    )
    logger.debug(f"Debugging mode enabled.")
    if (len(src.split(":")) > 1 and len(target.split(":")) > 1) or (
        len(src.split(":")) == 1 and len(target.split(":")) == 1
    ):
        msg = (
            "\nSRC and TARGET should be like:\n"
            "one argument - {container_name}:{container_path}\n"
            "another argument - {local_path}\n"
        )
        logger.error(msg)
        raise click.BadParameter(msg)
    if len(src.split(":")) > 1:
        container_name, container_path = src.split(":")
        logger.debug("File transfer started from container to local.")
        docker_local_transfer(
            c_name=container_name,
            c_path=pathlib.Path(container_path),
            l_path=pathlib.Path(target),
            target="local",
            chunk_size=buffer_length * 1024,
        )
    else:
        container_name, container_path = target.split(":")
        logger.debug("File transfer started from local to container.")
        docker_local_transfer(
            c_name=container_name,
            c_path=pathlib.Path(container_path),
            l_path=pathlib.Path(src),
            target="container",
            chunk_size=buffer_length * 1024,
        )


def docker_local_transfer(
    c_name: str,
    c_path: pathlib.Path,
    l_path: pathlib.Path,
    target: str,
    chunk_size: int = 2 * 1024,
):
    """Copy files between host machine and container.

    :param c_name: name of the container
    :param c_path: path in the continer
    :param l_path: path in host machine
    :param target: could be either `local` or `container`
    :param chunk_size: max chunk size
    :return:
    """
    try:
        container = client.containers.get(c_name)
    except docker.errors.NotFound:
        raise click.BadParameter(
            f"Container with name {c_name} doesn't exist."
        )
    # case where we copy file from container to host machine
    if target == "local":
        try:
            assert l_path.is_dir()
        except AssertionError:
            raise click.BadParameter("Local path should be a directory.")
        try:
            file_stream, _ = container.get_archive(
                path=c_path, chunk_size=chunk_size
            )
        except docker.errors.NotFound:
            raise click.BadParameter(
                f"{c_path} doesn't exist inside the container"
            )
        tar_bytes = BytesIO()
        for chunk in file_stream:
            tar_bytes.write(chunk)
        tar_bytes.seek(0)
        with tarfile.open(fileobj=tar_bytes) as tar:
            tar.extractall(path=l_path)
        logger.debug("Writing file to local - done.")
    # case where we copy file from host machine to container
    elif target == "container":
        try:
            assert l_path.exists()
        except AssertionError:
            raise click.BadParameter("Local path doesn't exists.")
        tar_bytes = BytesIO()
        with tarfile.open(fileobj=tar_bytes, mode="w") as tar:
            tar.add(l_path)
        tar_bytes.seek(0)
        try:
            container.put_archive(c_path, data=tar_bytes)
        except docker.errors.NotFound:
            raise click.BadParameter(
                f"{c_path} doesn't exists inside the container"
            )
        logger.debug("Writing file to container - done.")
