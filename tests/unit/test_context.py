import pathlib
import pytest
from yarl import URL

from neuro_flow.context import DepCtx, JobContext, NotAvailable, PipelineContext, Result
from neuro_flow.parser import parse_interactive, parse_pipeline
from neuro_flow.types import LocalPath, RemotePath


def test_inavailable_context_ctor() -> None:
    err = NotAvailable("job")
    assert err.args == ("Context job is not available",)
    assert str(err) == "Context job is not available"


async def test_ctx_flow(assets: pathlib.Path) -> None:
    workspace = assets / "jobs-minimal"
    config_file = workspace / ".neuro" / "jobs.yml"
    flow = parse_interactive(workspace, config_file)
    ctx = await JobContext.create(flow)
    assert ctx.flow.id == "jobs-minimal"
    assert ctx.flow.workspace == workspace
    assert ctx.flow.title == "jobs-minimal"


async def test_env_defaults(assets: pathlib.Path) -> None:
    workspace = assets / "jobs-full"
    config_file = workspace / ".neuro" / "jobs.yml"
    flow = parse_interactive(workspace, config_file)
    ctx = await JobContext.create(flow)
    assert ctx.env == {"global_a": "val-a", "global_b": "val-b"}


async def test_env_from_job(assets: pathlib.Path) -> None:
    workspace = assets / "jobs-full"
    config_file = workspace / ".neuro" / "jobs.yml"
    flow = parse_interactive(workspace, config_file)
    ctx = await JobContext.create(flow)
    ctx2 = await ctx.with_job("test_a")
    assert ctx2.env == {
        "global_a": "val-a",
        "global_b": "val-b",
        "local_a": "val-1",
        "local_b": "val-2",
    }


async def test_volumes(assets: pathlib.Path) -> None:
    workspace = assets / "jobs-full"
    config_file = workspace / ".neuro" / "jobs.yml"
    flow = parse_interactive(workspace, config_file)
    ctx = await JobContext.create(flow)
    assert ctx.volumes.keys() == {"volume_a", "volume_b"}

    assert ctx.volumes["volume_a"].id == "volume_a"
    assert ctx.volumes["volume_a"].remote == URL("storage:dir")
    assert ctx.volumes["volume_a"].mount == RemotePath("/var/dir")
    assert ctx.volumes["volume_a"].read_only
    assert ctx.volumes["volume_a"].local == LocalPath("dir")
    assert ctx.volumes["volume_a"].full_local_path == workspace / "dir"
    assert ctx.volumes["volume_a"].ref_ro == "storage:dir:/var/dir:ro"
    assert ctx.volumes["volume_a"].ref_rw == "storage:dir:/var/dir:rw"
    assert ctx.volumes["volume_a"].ref == "storage:dir:/var/dir:ro"

    assert ctx.volumes["volume_b"].id == "volume_b"
    assert ctx.volumes["volume_b"].remote == URL("storage:other")
    assert ctx.volumes["volume_b"].mount == RemotePath("/var/other")
    assert not ctx.volumes["volume_b"].read_only
    assert ctx.volumes["volume_b"].local is None
    assert ctx.volumes["volume_b"].full_local_path is None
    assert ctx.volumes["volume_b"].ref_ro == "storage:other:/var/other:ro"
    assert ctx.volumes["volume_b"].ref_rw == "storage:other:/var/other:rw"
    assert ctx.volumes["volume_b"].ref == "storage:other:/var/other:rw"


async def test_images(assets: pathlib.Path) -> None:
    workspace = assets / "jobs-full"
    config_file = workspace / ".neuro" / "jobs.yml"
    flow = parse_interactive(workspace, config_file)
    ctx = await JobContext.create(flow)
    assert ctx.images.keys() == {"image_a"}

    assert ctx.images["image_a"].id == "image_a"
    assert ctx.images["image_a"].ref == "image:banana"
    assert ctx.images["image_a"].context == LocalPath("dir")
    assert ctx.images["image_a"].full_context_path == workspace / "dir"
    assert ctx.images["image_a"].dockerfile == LocalPath("dir/Dockerfile")
    assert ctx.images["image_a"].full_dockerfile_path == workspace / "dir/Dockerfile"
    assert ctx.images["image_a"].build_args == ["--arg1", "val1", "--arg2=val2"]


async def test_defaults(assets: pathlib.Path) -> None:
    workspace = assets / "jobs-full"
    config_file = workspace / ".neuro" / "jobs.yml"
    flow = parse_interactive(workspace, config_file)
    ctx = await JobContext.create(flow)
    assert ctx.defaults.tags == {"tag-a", "tag-b"}
    assert ctx.defaults.workdir == RemotePath("/global/dir")
    assert ctx.defaults.life_span == 100800.0
    assert ctx.defaults.preset == "cpu-large"


async def test_job_root_ctx(assets: pathlib.Path) -> None:
    workspace = assets / "jobs-full"
    config_file = workspace / ".neuro" / "jobs.yml"
    flow = parse_interactive(workspace, config_file)
    ctx = await JobContext.create(flow)
    with pytest.raises(NotAvailable):
        ctx.job


async def test_job(assets: pathlib.Path) -> None:
    workspace = assets / "jobs-full"
    config_file = workspace / ".neuro" / "jobs.yml"
    flow = parse_interactive(workspace, config_file)
    ctx = await JobContext.create(flow)

    ctx2 = await ctx.with_job("test_a")
    assert ctx2.job.id == "test_a"
    assert ctx2.job.title == "Job title"
    assert ctx2.job.name == "job-name"
    assert ctx2.job.image == "image:banana"
    assert ctx2.job.preset == "cpu-small"
    assert ctx2.job.http_port == 8080
    assert not ctx2.job.http_auth
    assert ctx2.job.entrypoint == "bash"
    assert ctx2.job.cmd == "echo abc"
    assert ctx2.job.workdir == RemotePath("/local/dir")
    assert ctx2.job.volumes == ["storage:dir:/var/dir:ro", "storage:dir:/var/dir:ro"]
    assert ctx2.job.tags == {"tag-1", "tag-2", "tag-a", "tag-b"}
    assert ctx2.job.life_span == 10500.0
    assert ctx2.job.port_forward == ["2211:22"]
    assert ctx2.job.detach
    assert ctx2.job.browse


async def test_pipline_root_ctx(assets: pathlib.Path) -> None:
    workspace = assets
    config_file = workspace / "pipeline-minimal.yml"
    flow = parse_pipeline(workspace, config_file)
    ctx = await PipelineContext.create(flow)
    with pytest.raises(NotAvailable):
        ctx.batch


async def test_pipeline_minimal_ctx(assets: pathlib.Path) -> None:
    workspace = assets
    config_file = workspace / "pipeline-minimal.yml"
    flow = parse_pipeline(workspace, config_file)
    ctx = await PipelineContext.create(flow)

    ctx2 = await ctx.with_batch("test_a", needs={})
    assert ctx2.batch.id == "test_a"
    assert ctx2.batch.real_id == "test_a"
    assert ctx2.batch.needs == set()
    assert ctx2.batch.title == "Batch title"
    assert ctx2.batch.name == "job-name"
    assert ctx2.batch.image == "image:banana"
    assert ctx2.batch.preset == "cpu-small"
    assert ctx2.batch.http_port == 8080
    assert not ctx2.batch.http_auth
    assert ctx2.batch.entrypoint == "bash"
    assert ctx2.batch.cmd == "echo abc"
    assert ctx2.batch.workdir == RemotePath("/local/dir")
    assert ctx2.batch.volumes == ["storage:dir:/var/dir:ro", "storage:dir:/var/dir:ro"]
    assert ctx2.batch.tags == {"tag-1", "tag-2", "tag-a", "tag-b"}
    assert ctx2.batch.life_span == 10500.0

    assert ctx.order == [{"test_a"}]
    assert ctx2.matrix == {}


async def test_pipeline_seq(assets: pathlib.Path) -> None:
    workspace = assets
    config_file = workspace / "pipeline-seq.yml"
    flow = parse_pipeline(workspace, config_file)
    ctx = await PipelineContext.create(flow)

    ctx2 = await ctx.with_batch(
        "batch-2", needs={"batch-1": DepCtx(Result.SUCCESS, {})}
    )
    assert ctx2.batch.id is None
    assert ctx2.batch.real_id == "batch-2"
    assert ctx2.batch.needs == {"batch-1"}
    assert ctx2.batch.title is None
    assert ctx2.batch.name is None
    assert ctx2.batch.image == "ubuntu"
    assert ctx2.batch.preset == "cpu-small"
    assert ctx2.batch.http_port is None
    assert not ctx2.batch.http_auth
    assert ctx2.batch.entrypoint is None
    assert ctx2.batch.cmd == "bash -euxo pipefail -c 'echo def'"
    assert ctx2.batch.workdir is None
    assert ctx2.batch.volumes == []
    assert ctx2.batch.tags == {"flow:pipeline-seq", "batch:batch-2"}
    assert ctx2.batch.life_span is None

    assert ctx.order == [{"batch-1"}, {"batch-2"}]
    assert ctx2.matrix == {}


async def test_pipeline_needs(assets: pathlib.Path) -> None:
    workspace = assets
    config_file = workspace / "pipeline-needs.yml"
    flow = parse_pipeline(workspace, config_file)
    ctx = await PipelineContext.create(flow)

    ctx2 = await ctx.with_batch(
        "batch-2", needs={"batch_a": DepCtx(Result.SUCCESS, {})}
    )
    assert ctx2.batch.id is None
    assert ctx2.batch.real_id == "batch-2"
    assert ctx2.batch.needs == {"batch_a"}
    assert ctx2.batch.title is None
    assert ctx2.batch.name is None
    assert ctx2.batch.image == "ubuntu"
    assert ctx2.batch.preset == "cpu-small"
    assert ctx2.batch.http_port is None
    assert not ctx2.batch.http_auth
    assert ctx2.batch.entrypoint is None
    assert ctx2.batch.cmd == "bash -euxo pipefail -c 'echo def'"
    assert ctx2.batch.workdir is None
    assert ctx2.batch.volumes == []
    assert ctx2.batch.tags == {"flow:pipeline-needs", "batch:batch-2"}
    assert ctx2.batch.life_span is None

    assert ctx.order == [{"batch_a"}, {"batch-2"}]
    assert ctx2.matrix == {}


async def test_pipeline_matrix(assets: pathlib.Path) -> None:
    workspace = assets
    config_file = workspace / "pipeline-matrix.yml"
    flow = parse_pipeline(workspace, config_file)
    ctx = await PipelineContext.create(flow)

    assert ctx.order == [
        {"batch-1-o2-t1", "batch-1-o2-t2", "batch-1-o1-t1", "batch-1-e3-o3-t3"}
    ]

    ctx2 = await ctx.with_batch("batch-1-o2-t2", needs={})
    assert ctx2.batch.id is None
    assert ctx2.batch.real_id == "batch-1-o2-t2"
    assert ctx2.batch.needs == set()
    assert ctx2.batch.title is None
    assert ctx2.batch.name is None
    assert ctx2.batch.image == "ubuntu"
    assert ctx2.batch.preset is None
    assert ctx2.batch.http_port is None
    assert not ctx2.batch.http_auth
    assert ctx2.batch.entrypoint is None
    assert ctx2.batch.cmd == "echo abc"
    assert ctx2.batch.workdir is None
    assert ctx2.batch.volumes == []
    assert ctx2.batch.tags == {"flow:pipeline-matrix", "batch:batch-1-o2-t2"}
    assert ctx2.batch.life_span is None

    assert ctx2.matrix == {"one": "o2", "two": "t2"}
