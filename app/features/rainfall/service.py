import os
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

class RainfallService:
    _df_cache: Optional[pd.DataFrame] = None

    @classmethod
    def _load_data(cls) -> Optional[pd.DataFrame]:
        if cls._df_cache is not None:
            return cls._df_cache

        paths = [
            "/app/data/era5_clean.csv",
            os.path.join(os.getcwd(), "data/era5_clean.csv"),
            "/app/data/era5_hidrologi_indonesia.csv",
            os.path.join(os.getcwd(), "data/era5_hidrologi_indonesia.csv"),
        ]

        for p in paths:
            if os.path.exists(p):
                try:
                    df = pd.read_csv(p)
                    col = "curah_hujan_mm" if "curah_hujan_mm" in df.columns else "tp_mm"
                    if col in df.columns:
                        cls._df_cache = df
                        return cls._df_cache
                except Exception as e:
                    print(f"[RainfallService Error] Failed to load {p}: {e}")
        return None

    @classmethod
    def get_rainfall_stats(cls, limit: int = 1000) -> Dict[str, Any]:
        """
        Get precipitation / rainfall (curah hujan) statistics and grid points from ERA5 dataset.
        """
        df = cls._load_data()
        if df is not None:
            col = "curah_hujan_mm" if "curah_hujan_mm" in df.columns else "tp_mm"
            sample = df.sample(min(limit, len(df))) if len(df) > limit else df

            records = sample[["latitude", "longitude", col, "waktu" if "waktu" in sample.columns else "valid_time"]].rename(
                columns={col: "rainfall_mm", "valid_time": "waktu"}
            ).to_dict(orient="records")

            return {
                "status": "success",
                "total_records": len(df),
                "sample_size": len(records),
                "summary": {
                    "mean_rainfall_mm": round(float(df[col].mean()), 2),
                    "min_rainfall_mm": round(float(df[col].min()), 2),
                    "max_rainfall_mm": round(float(df[col].max()), 2),
                    "total_rainfall_mm": round(float(df[col].sum()), 2),
                    "unit": "mm"
                },
                "data": records
            }

        return {
            "status": "simulated",
            "total_records": 100,
            "sample_size": 10,
            "summary": {
                "mean_rainfall_mm": 5.2,
                "min_rainfall_mm": 0.0,
                "max_rainfall_mm": 45.0,
                "unit": "mm"
            },
            "data": []
        }

    @classmethod
    def get_rainfall_at_point(cls, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get nearest rainfall record at specified lat, lon.
        """
        df = cls._load_data()
        if df is not None:
            col = "curah_hujan_mm" if "curah_hujan_mm" in df.columns else "tp_mm"
            dist = (df["latitude"] - lat)**2 + (df["longitude"] - lon)**2
            nearest_idx = dist.idxmin()
            row = df.loc[nearest_idx]

            return {
                "status": "success",
                "target_lat": lat,
                "target_lon": lon,
                "nearest_lat": float(row["latitude"]),
                "nearest_lon": float(row["longitude"]),
                "rainfall_mm": round(float(row[col]), 2),
                "timestamp": str(row.get("waktu", row.get("valid_time", ""))),
                "unit": "mm"
            }

        return {
            "status": "simulated",
            "target_lat": lat,
            "target_lon": lon,
            "rainfall_mm": round(float(np.random.exponential(5.0)), 2),
            "unit": "mm"
        }
