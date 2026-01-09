# 🌐 Webアプリとしての公開手順 (Streamlit Community Cloud)

作成したアプリを無料でWeb公開し、スマホやPCからアクセスできるようにする手順です。

## 前提条件
*   GitHubアカウントを持っていること
*   Streamlit Community Cloudアカウントを持っていること（GitHub連携で作成可能）

## 手順 1: GitHubへのアップロード（初回のみ）

まず、このプロジェクトをGitHubのリポジトリとして保存します。
※ 2回目以降（更新時）は「運用: アプリの更新手順」を参照してください。

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

## 手順 2: Streamlit Community Cloud でのデプロイ（初回のみ）

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
## 運用: アプリの更新手順（2回目以降）

コードを修正したり、新しいGPXファイルを追加した場合は、ターミナルで以下の3行を実行するだけでWebアプリが自動更新されます。

```bash
git add .
git commit -m "アプリを更新"
git push
```
数分後、Web上のアプリに反映されます。(`git init` や `remote add` は不要です)

---

## 手順 4: ブログへの埋め込み (akirun.netへの実装)

WordPressなどのブログ記事内に、この計算機を埋め込んで表示させることができます。

1.  上記の手順で発行された **アプリのURL** をコピーします（例: `https://your-app-name.streamlit.app`）。
2.  ブログの編集画面（HTML編集 / カスタムHTMLブロック）で、以下のコードを貼り付けます。
    
    ```html
    <iframe
      src="https://your-app-name.streamlit.app/?embed=true"
      height="800"
      width="100%"
      style="border:none;"
      title="Marathon Pacer">
    </iframe>
    ```

    *   `src`: コピーしたURLの末尾に `/?embed=true` をつけると、ヘッダー等の余計な装飾が消えて綺麗に埋め込めます。
    *   `height`: 高さは必要に応じて調整してください（例: `1000` など）。

これにより、ブログの読者は記事ページから移動することなく、そのままシミュレーションを実行できるようになります。
