# 示例

[English](README.md)

sample-work-kb/ 是一个完全虚构的小型工作库，内容是 Project Atlas（与 Riverside Clinic 合作的试点项目）。库里有三份来源、它们的卡片，以及由卡片生成的主题页。可以用 Obsidian 打开，也可以登记后试用三个技能。

登记前先把 sample-work-kb/ 复制到自己的文件夹里，这样示例本身保持不变（技能会写入所用的库）。然后在知识库客户端的「安装与建库」里，或在 `python3 install.py` 里，把这份副本选作知识库文件夹：已有知识库的文件夹会按原样登记，不改动其中任何文件。也可以手动在注册表里加一条：

```json
{"schema": 1, "libraries": [{"id": "sample", "label": "Sample Work",
  "scope": "Project Atlas, a fictional pilot run with Riverside Clinic (demo only)",
  "backend": {"type": "local", "root": "<sample-work-kb 副本的路径>"}}]}
```

依次试试：
1. 「Atlas 试点什么时候结束？」（kb-query：查主题页和卡片；延期写在 decision logs 主题页上）
2. 「记一下：试点评审改到周四。」（kb-note：这句话成为 Sources/ 里的一份来源并抽出卡片，涉及的主题页重建）
3. 「入库：<路径>/examples/new-material」（kb-ingest：生成批文件、抽卡片、核对引文，再重建涉及的主题页），或者在客户端里用这个库下面的「入库」选这个文件夹

示例是英文库，回答会用英文。

示例的生成方式：sample-materials/ 是三份来源文档（邮件，转换器按纯文本读取），sample-work-cards.jsonl 是为它们写的卡片。tests/test_examples.py 对它们运行转换器、引文核对和 ingest.py，并检查结果与示例库一致；改了脚本之后，用 SAMPLE_UPDATE=1 python3 -m unittest tests.test_examples 重新生成。
