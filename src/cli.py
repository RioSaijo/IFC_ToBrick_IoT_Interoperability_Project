import argparse, json
from app.pipeline import run_all

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ifc", required=True)
    p.add_argument("--points-csv", required=True)
    p.add_argument("--base-ns", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--csvw", default=None)
    args = p.parse_args()

    res = run_all(
        ifc_path=args.ifc,
        points_csv=args.points_csv,
        base_ns=args.base_ns,
        out_ttl=args.out,
        csvw_metadata_path=args.csvw,
        crosswalk_equip=None,
        crosswalk_points=None,
    )
    print(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()
