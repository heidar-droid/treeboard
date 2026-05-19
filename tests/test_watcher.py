import asyncio
import pathlib

import pytest

from arboviz.watcher import TreeWatcher


@pytest.mark.asyncio
async def test_watcher_emits_create(tmp_tree):
    watcher = TreeWatcher(tmp_tree, respect_gitignore=True, include_dotfiles=False)
    watcher.start()
    try:
        new = tmp_tree / "ai-assets" / "fresh.md"
        # give the watcher a moment to start
        await asyncio.sleep(0.2)
        new.write_text("hi")
        evt = await asyncio.wait_for(watcher.queue.get(), timeout=2.0)
        assert evt["type"] in ("created", "modified")
        assert evt["path"].endswith("fresh.md")
    finally:
        watcher.stop()


@pytest.mark.asyncio
async def test_watcher_filters_gitignored(tmp_tree):
    watcher = TreeWatcher(tmp_tree, respect_gitignore=True, include_dotfiles=False)
    watcher.start()
    try:
        await asyncio.sleep(0.2)
        (tmp_tree / "node_modules" / "new.js").write_text("x")
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(watcher.queue.get(), timeout=0.8)
    finally:
        watcher.stop()
