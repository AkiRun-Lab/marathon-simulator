# 🌐 Webアプリとしての公開手順 (Streamlit Community Cloud)

作成したアプリを無料でWeb公開し、スマホやPCからアクセスできるようにする手順です。

## 前提条件
*   GitHubアカウントを持っていること
*   Streamlit Community Cloudアカウントを持っていること（GitHub連携で作成可能）

## 手順 1: GitHubへのアップロード

まず、このプロジェクトをGitHubのリポジトリとして保存します。

1.  **TerminalでGitの初期設定**
    （まだしていなければ）プロジェクトフォルダで以下を実行します。
    ```bash
    git init
    git add .
    git commit -m "Initial commit for Ehime Marathon Pacer"
    ```

2.  **GitHubでリポジトリ作成**
    *   [GitHub](https://github.com) にアクセスし、右上の「+」→「New repository」をクリック。
    *   **Repository name**: `ehime-marathon-pacer` など好きな名前を入力。
    *   **Public/Private**: どちらでもOKですが、無料版Streamlit CloudはPublicのみの場合があります（要確認）。Privateでもデプロイ可能ですが制限がある場合があります。
    *   「Create repository」をクリック。

3.  **コードのプッシュ**
    *   作成後の画面に表示されるコマンド（`…or push an existing repository from the command line`）をコピーして、Terminalで実行します。例：
    ```bash
    git remote add origin https://github.com/YOUR_USERNAME/ehime-marathon-pacer.git
    git branch -M main
    git push -u origin main
    ```

## 手順 2: Streamlit Community Cloud でのデプロイ

1.  [Streamlit Community Cloud](https://streamlit.io/cloud) にログインします。
2.  **「New app」** ボタンをクリックします。
3.  **「Use existing repo」** を選択します。
4.  以下の設定を入力します：
    *   **Repository**: 手順1で作成した `YOUR_USERNAME/ehime-marathon-pacer` を選択。
    *   **Branch**: `main`
    *   **Main file path**: `app.py`
5.  **「Deploy!」** をクリックします。

## 手順 3: 完了！

1〜2分待つと、デプロイが完了し、アプリのURL（例: `https://ehime-marathon-pacer.streamlit.app`）が発行されます。
このURLをスマホに送れば、大会当日の朝やスタート前にいつでもプランを確認できます！

---
### 注意点: データの追加
新しいGPXファイルを追加したい場合は、PCのローカルフォルダに追加したあと、再度GitでCommit & Pushしてください。
```bash
git add data/
git commit -m "Add new marathon course"
git push
```
自動的にWebアプリ側も更新されます。
