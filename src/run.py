#環境依存処理
#このファイルは、IFC -> Brick 変換パイプラインのエントリーポイントである。
#ユーザーからIFCファイルのパスと出力ディレクトリを入力させ、パイプラインを実行する。

#環境
import sys
from pathlib import Path
from src.app.pipeline import run_pipeline

#
def init_runtime():
    project_root = Path(__file__).resolve().parent.parent
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.append(str(src_path))

#
def main():

    init_runtime()
#ここで実装中断



    print("IFC -> Brick 変換パイプラインを開始する")
    ifc_path = input("IFCファイルのパスを入力せよ : ")
    output_dir = input("出力ディレクトリを入力せよ : ")

    run_pipeline(
        ifc_path="data/input/model.ifc",
        output_dir="data/output"
    )

if __name__ == "__main__":
    main()