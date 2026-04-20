from src.app.pipeline import run_pipeline

def main():
    run_pipeline(
        ifc_path="data/input/model.ifc",
        output_dir="data/output"
    )

if __name__ == "__main__":
    main()