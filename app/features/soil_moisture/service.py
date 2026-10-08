import os
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

class SoilMoistureService:
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
                    col = "soil_moisture" if "soil_moisture" in df.columns else "swvl1"
                    if col in df.columns:
                        cls._df_cache = df
                        return cls._df_cache
                except Exception as e:
                    print(f"[SoilMoistureService Error] Failed to load {p}: {e}")
        return None

    @classmethod
    def get_soil_moisture_stats(cls, limit: int = 1000) -> Dict[str, Any]:
        """
        Get soil moisture (kelembaban tanah) statistics and grid points from ERA5 dataset.
        """
        df = cls._load_data()
        if df is not None:
            col = "soil_moisture" if "soil_moisture" in df.columns else "swvl1"
            sample = df.sample(min(limit, len(df))) if len(df) > limit else df

            records = sample[["latitude", "longitude", col, "waktu" if "waktu" in sample.columns else "valid_time"]].rename(
                columns={col: "soil_moisture", "valid_time": "waktu"}
            ).to_dict(orient="records")

            return {
                "status": "success",
                "total_records": len(df),
                "sample_size": len(records),
                "summary": {
                    "mean_soil_moisture": round(float(df[col].mean()), 4),
                    "min_soil_moisture": round(float(df[col].min()), 4),
                    "max_soil_moisture": round(float(df[col].max()), 4),
                    "std_soil_moisture": round(float(df[col].std()), 4),
                    "unit": "m³/m³"
                },
                "data": records
            }

        return {
            "status": "simulated",
            "total_records": 100,
            "sample_size": 10,
            "summary": {
                "mean_soil_moisture": 0.35,
                "min_soil_moisture": 0.10,
                "max_soil_moisture": 0.55,
                "unit": "m³/m³"
            },
            "data": []
        }

    @classmethod
    def get_soil_moisture_at_point(cls, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get nearest soil moisture record at specified lat, lon.
        """
        df = cls._load_data()
        if df is not None:
            col = "soil_moisture" if "soil_moisture" in df.columns else "swvl1"
            dist = (df["latitude"] - lat)**2 + (df["longitude"] - lon)**2
            nearest_idx = dist.idxmin()
            row = df.loc[nearest_idx]

            return {
                "status": "success",
                "target_lat": lat,
                "target_lon": lon,
                "nearest_lat": float(row["latitude"]),
                "nearest_lon": float(row["longitude"]),
                "soil_moisture": round(float(row[col]), 4),
                "timestamp": str(row.get("waktu", row.get("valid_time", ""))),
                "unit": "m³/m³"
            }

        return {
            "status": "simulated",
            "target_lat": lat,
            "target_lon": lon,
            "soil_moisture": round(float(np.random.uniform(0.2, 0.5)), 4),
            "unit": "m³/m³"
        }
