import os
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

class TemperatureService:
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
                    temp_col = "suhu_celsius" if "suhu_celsius" in df.columns else "t2m_celsius"
                    if temp_col in df.columns:
                        cls._df_cache = df
                        return cls._df_cache
                except Exception as e:
                    print(f"[TemperatureService Error] Failed to load {p}: {e}")
        return None

    @classmethod
    def get_temperature_stats(cls, limit: int = 1000) -> Dict[str, Any]:
        """
        Get air temperature (suhu udara) statistics and grid points from ERA5 dataset.
        """
        df = cls._load_data()
        if df is not None:
            col = "suhu_celsius" if "suhu_celsius" in df.columns else "t2m_celsius"
            sample = df.sample(min(limit, len(df))) if len(df) > limit else df

            records = sample[["latitude", "longitude", col, "waktu" if "waktu" in sample.columns else "valid_time"]].rename(
                columns={col: "temperature_celsius", "valid_time": "waktu"}
            ).to_dict(orient="records")

            return {
                "status": "success",
                "total_records": len(df),
                "sample_size": len(records),
                "summary": {
                    "mean_celsius": round(float(df[col].mean()), 2),
                    "min_celsius": round(float(df[col].min()), 2),
                    "max_celsius": round(float(df[col].max()), 2),
                    "std_celsius": round(float(df[col].std()), 2),
                    "unit": "°C"
                },
                "data": records
            }

        # Fallback simulation
        return {
            "status": "simulated",
            "total_records": 100,
            "sample_size": 10,
            "summary": {
                "mean_celsius": 28.5,
                "min_celsius": 22.0,
                "max_celsius": 35.0,
                "unit": "°C"
            },
            "data": []
        }

    @classmethod
    def get_temperature_at_point(cls, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get nearest air temperature record at specified lat, lon.
        """
        df = cls._load_data()
        if df is not None:
            col = "suhu_celsius" if "suhu_celsius" in df.columns else "t2m_celsius"
            # Compute Euclidean distance to lat, lon
            dist = (df["latitude"] - lat)**2 + (df["longitude"] - lon)**2
            nearest_idx = dist.idxmin()
            row = df.loc[nearest_idx]

            return {
                "status": "success",
                "target_lat": lat,
                "target_lon": lon,
                "nearest_lat": float(row["latitude"]),
                "nearest_lon": float(row["longitude"]),
                "temperature_celsius": round(float(row[col]), 2),
                "timestamp": str(row.get("waktu", row.get("valid_time", ""))),
                "unit": "°C"
            }

        return {
            "status": "simulated",
            "target_lat": lat,
            "target_lon": lon,
            "temperature_celsius": round(float(np.random.normal(28.5, 2.0)), 2),
            "unit": "°C"
        }
