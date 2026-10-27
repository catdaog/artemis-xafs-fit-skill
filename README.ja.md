# XAFS Fit Skill · EXAFS + XANES

[![test](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml/badge.svg)](https://github.com/catdaog/artemis-xafs-fit-skill/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)

**1つのスキルで2種類のフィッティング：EXAFSの定量解析と、XANESの理論計算・局所構造フィッティング。**

`artemis-xafs-fit-skill` はローカルの実際の計算プログラムを実行し、元データ、構造の出典、入出力、解析記録を保存します。各手法を単独で使用でき、同じ構造候補を両方の結果から検討することもできます。

## フィッティング手法を選ぶ

| 項目 | EXAFSフィッティング | XANES（吸収端近傍構造）フィッティング |
|---|---|---|
| 主な目的 | 配位数、結合距離、Debye–Waller因子、散乱経路の解析 | 配位構造候補や局所幾何構造が吸収端近傍のスペクトル形状を再現するかの検討 |
| 計算プログラム | Athena / Artemis / Demeter + FEFF | FDMNES：Green関数による多重散乱法、または有限差分法 |
| 主な入力 | 数値スペクトルまたは重み付け前のχ(k)、処理条件、同じ吸収端の標準試料、構造／FEFFモデル | エネルギー–吸収強度の数値データ、校正・規格化の根拠、原子構造候補 |
| 解析の流れ | 標準試料からS₀²を求める → 経路確認 → 段階的フィッティング → パラメータ検討 | クラスター作成 → 収束確認 → スペクトル位置合わせ → 少数の幾何パラメータ最適化 → 複数初期値の比較 |
| 出力 | 再読み込み可能なDPJ、k1/k2/k3・R1/R2/R3数値表、パラメータ表、解析記録 | 測定値・計算値・残差の表、パラメータ・モデル比較、PNG/SVG、構造、入力、ログ |
| 詳細 | [EXAFSガイド（英語）](references/exafs-guide.en.md) | [XANES／FDMNESガイド（英語）](references/xanes-fdmnes.md) |

**XANESには独立した手順と出力仕様があります。EXAFSのS₀²校正、k/R範囲、DPJは前提条件ではありません。** 参照スペクトルの線形結合フィッティング（LCF）は別の手法であり、このXANES機能には実装されていません。

## 呼び出し例

**EXAFS：**

```text
$artemis-xafs-fit-skill を使ってEXAFSデータをフィッティングしてください。同じ吸収端で配位数が既知の標準試料からS₀²を求めてから試料を解析し、再読み込み可能なDPJ、k/R数値表、パラメータ表、解析記録を出力してください。
```

**XANES：**

```text
$artemis-xafs-fit-skill を使い、単原子サイトを含む試料について、FDMNESによる吸収端近傍の計算と構造フィッティングを行ってください。組成と既存のEXAFS結果に基づいて候補モデルを作成し、収束と複数の初期値を確認して、重ね合わせ図、残差、再現に必要なファイルを出力してください。
```

## 必要な入力

- 共通：吸収元素・吸収端、試料とファイルの対応、測定条件、各列の意味、エネルギー校正の根拠、数値スペクトル。繰り返し測定も保存してください。
- EXAFS：可能であれば同じ吸収端の標準試料、Athena `.prj`、重み付け前のχ(k)と処理条件、CIF／FEFFファイル。既存解析の続行には `.fpj`／`.dpj` とログも添付してください。
- XANES：規格化済みμ(E)、または適切な規格化範囲を指定できるμ(E)。検出器の生カウントは測定方式に応じて先に変換する必要があります。構造はCIFまたは明示的な原子座標を使用し、仮説に基づく構造には候補であることを明記してください。

スクリーンショットは説明に利用できますが、実際のフィッティングには数値データが必要です。構造ファイルがなければ、組成や独立した証拠から候補モデルを先に作成できます。

## インストールと実行

[Release](https://github.com/catdaog/artemis-xafs-fit-skill/releases)をダウンロードするか、リポジトリをクローンします。フォルダー名を `artemis-xafs-fit-skill` とし、skillsディレクトリ（例：`~/.codex/skills/`）に配置してください。そのフォルダーで、使用するPython環境に依存パッケージをインストールします。

```shell
python -m pip install -r requirements.txt -r requirements-xanes.txt
```

EXAFSには [Demeter](https://bruceravel.github.io/demeter/)／[FEFF](https://feff.phys.washington.edu/feffproject-feff-download.html)を別途インストールします。XANES用FDMNESは[公式配布ページ](https://fdmnes.neel.cnrs.fr/download/)から取得してください。外部プログラムは同梱していません。Windowsでは次のように実行できます。

```powershell
.\scripts\run_xanes.ps1 -Mode install -Archive C:\path\fdmnes.zip
.\scripts\run_xanes.ps1 -Mode probe
.\scripts\run_xanes.ps1 -Mode simulate -Config examples\xanes\fe-n4.json -Output C:\work\xanes_sim
.\scripts\run_xanes.ps1 -Mode fit -Config C:\work\xanes.json -Output C:\work\xanes_fit
```

既存の実行ファイルは `FDMNES_EXE` でも指定できます。設定の詳細とコマンドはXANESガイドを参照してください。各言語ページは使用説明の翻訳であり、プログラムの引数名やファイル名は共通です。

## 結果と検証

v1.4.0は、実際のFDMNESを用いた合成スペクトルからのパラメータ回復と有限差分計算を含む23件のローカルテストに合格しました。GitHub CIでは外部エンジンを必要としないテストを実行します。合成データの試験はソフトウェアの動作とパラメータ回復を検証するもので、実在の触媒構造を実証するものではありません。

理論スペクトルの計算、位置合わせ、構造フィッティングを区別して記録します。数値的に収束しても、残差、相関、パラメータ境界、初期値依存性の確認が必要です。XANESの一致だけでは単原子分散や構造の一意性は証明できません。

## ドキュメントと例

- [EXAFS詳細ガイド（英語）](references/exafs-guide.en.md)
- [XANES／FDMNESの手順（英語）](references/xanes-fdmnes.md)
- [EXAFS一括解析テンプレート](examples/pipeline.template.json)
- [XANES設定例：説明用の5原子モデル](examples/xanes/fe-n4.json)
- [スキルの入口と制約（英語）](SKILL.md)
- [変更履歴（中国語／英語）](CHANGELOG.md)

ライセンス：スキルのソースコードは [MIT](LICENSE)です。外部計算プログラムにはそれぞれのライセンスが適用されます。

[中文](README.md) · [English](README.en.md) · [Deutsch](README.de.md) · [日本語](README.ja.md) · [Français](README.fr.md)
