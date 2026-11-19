# Veraphifiy

Code memory for each project version. Veraphifiy archives an evidence graph against the exact project commit and uses it to look up implementation citations for a selected version.

We use and support the open-source Graphify project. Veraphifiy is developed and maintained independently of Graphify Labs.

## Open the candidate

Clone the candidate and run its entry point with Node.js 24 and Git.

```sh
git clone --branch work/veraphifiy-v0.0.9 https://github.com/vixttha/Veraphifiy.git
cd Veraphifiy
node veraphifiy.mjs --help
```

## Archive and find evidence

Supply the paired `graph.json` and `receipt.json` produced by the existing pinned Graphify feature-evidence builder (Graphify `0.9.109`). The source checkout must contain the exact commit claimed by the receipt.

```sh
node veraphifiy.mjs import --archive ./archive --project owner/repo --version v1.2.3 \
  --source COMMIT_SHA --checkout ../project --evidence ../graph-output
node veraphifiy.mjs verify --archive ./archive --project owner/repo --version v1.2.3
node veraphifiy.mjs lookup --archive ./archive --project owner/repo --version v1.2.3 \
  --feature feature:export
```

The project name must match the receipt. Each archive entry preserves the graph, receipt and verified source blobs. Importing identical evidence is repeatable. An existing version can only be read or replayed. To check against a separately known commit, include `--source` when reading an archive.

Keep archives that contain private source on private storage. The public Test Vault uploads only disposable fixture archives. [Test Vault](test-vault/README.md) · [v0.0.9 tracker](https://github.com/vixttha/Veraphifiy/issues/21)
