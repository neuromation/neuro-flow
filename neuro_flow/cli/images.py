import click

from neuro_flow.cli.click_types import LIVE_IMAGE_OR_ALL
from neuro_flow.cli.utils import argument, wrap_async
from neuro_flow.live_runner import LiveRunner
from neuro_flow.parser import ConfigDir, find_live_config


@click.command()
@argument("image", type=LIVE_IMAGE_OR_ALL)
@wrap_async()
async def build(config_dir: ConfigDir, image: str) -> None:
    """Build an image.

    Assemble the IMAGE remotely and publish it.
    """
    config_path = find_live_config(config_dir)
    async with LiveRunner(config_path.workspace, config_path.config_file) as runner:
        if image == "ALL":
            await runner.build_all()
        else:
            await runner.build(image)