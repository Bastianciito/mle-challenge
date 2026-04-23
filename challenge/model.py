import pandas as pd

from typing import Tuple, Union, List
from datetime import datetime
import numpy as np
from sklearn.linear_model import LogisticRegression
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.utils import shuffle


class DelayModel:

    def __init__(self):
        self._model = None  # Model should be saved in this attribute.
        self._feature_cols = [
            "OPERA_Latin American Wings",
            "MES_7",
            "MES_10",
            "OPERA_Grupo LATAM",
            "MES_12",
            "TIPOVUELO_I",
            "MES_4",
            "MES_11",
            "OPERA_Sky Airline",
            "OPERA_Copa Air",
        ]
        self.threshold_in_minutes = 15

    def get_period_day(self, date):
        date_time = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").time()
        morning_min = datetime.strptime("05:00", "%H:%M").time()
        morning_max = datetime.strptime("11:59", "%H:%M").time()
        afternoon_min = datetime.strptime("12:00", "%H:%M").time()
        afternoon_max = datetime.strptime("18:59", "%H:%M").time()
        evening_min = datetime.strptime("19:00", "%H:%M").time()
        evening_max = datetime.strptime("23:59", "%H:%M").time()
        night_min = datetime.strptime("00:00", "%H:%M").time()
        night_max = datetime.strptime("4:59", "%H:%M").time()

        if date_time > morning_min and date_time < morning_max:
            return "mañana"
        elif date_time > afternoon_min and date_time < afternoon_max:
            return "tarde"
        elif (date_time > evening_min and date_time < evening_max) or (
            date_time > night_min and date_time < night_max
        ):
            return "noche"

    from datetime import datetime

    def is_high_season(self, fecha):
        fecha_anho = int(fecha.split("-")[0])
        fecha = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
        range1_min = datetime.strptime("15-Dec", "%d-%b").replace(year=fecha_anho)
        range1_max = datetime.strptime("31-Dec", "%d-%b").replace(year=fecha_anho)
        range2_min = datetime.strptime("1-Jan", "%d-%b").replace(year=fecha_anho)
        range2_max = datetime.strptime("3-Mar", "%d-%b").replace(year=fecha_anho)
        range3_min = datetime.strptime("15-Jul", "%d-%b").replace(year=fecha_anho)
        range3_max = datetime.strptime("31-Jul", "%d-%b").replace(year=fecha_anho)
        range4_min = datetime.strptime("11-Sep", "%d-%b").replace(year=fecha_anho)
        range4_max = datetime.strptime("30-Sep", "%d-%b").replace(year=fecha_anho)

        if (
            (fecha >= range1_min and fecha <= range1_max)
            or (fecha >= range2_min and fecha <= range2_max)
            or (fecha >= range3_min and fecha <= range3_max)
            or (fecha >= range4_min and fecha <= range4_max)
        ):
            return 1
        else:
            return 0

    def get_min_diff(self, data):
        fecha_o = datetime.strptime(data["Fecha-O"], "%Y-%m-%d %H:%M:%S")
        fecha_i = datetime.strptime(data["Fecha-I"], "%Y-%m-%d %H:%M:%S")
        min_diff = ((fecha_o - fecha_i).total_seconds()) / 60
        return min_diff

    def preprocess(
        self, data: pd.DataFrame, target_column: str = None
    ) -> Union(Tuple[pd.DataFrame, pd.DataFrame], pd.DataFrame):
        """
        Prepare raw data for training or predict.

        Args:
            data (pd.DataFrame): raw data.
            target_column (str, optional): if set, the target is returned.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: features and target.
            or
            pd.DataFrame: features.
        """
        try:
            if target_column is not None:
                # prepare data for training
                data_ = data.copy()
                data_["period_day"] = data_["Fecha-I"].apply(self.get_period_day)
                data_["high_season"] = data_["Fecha-I"].apply(self.is_high_season)
                data_["min_diff"] = data_.apply(self.get_min_diff, axis=1)
                data_["delay"] = np.where(
                    data_["min_diff"] > self.threshold_in_minutes, 1, 0
                )
                data_ = data_[
                    ["OPERA", "MES", "TIPOVUELO", "SIGLADES", "DIANOM", "delay"]
                ]

                features = pd.concat(
                    [
                        pd.get_dummies(data_["OPERA"], prefix="OPERA"),
                        pd.get_dummies(data_["TIPOVUELO"], prefix="TIPOVUELO"),
                        pd.get_dummies(data_["MES"], prefix="MES"),
                    ],
                    axis=1,
                )
                target = data_[[target_column]]
                return features[self._feature_cols], target
            else:
                # is data for inference
                data_ = data.copy()
                features = pd.concat(
                    [
                        pd.get_dummies(data_["OPERA"], prefix="OPERA"),
                        pd.get_dummies(data_["TIPOVUELO"], prefix="TIPOVUELO"),
                        pd.get_dummies(data_["MES"], prefix="MES"),
                    ],
                    axis=1,
                )
                return features.reindex(columns=self._feature_cols, fill_value=0)
        except Exception as e:
            raise Exception(e)

    def fit(self, features: pd.DataFrame, target: pd.DataFrame) -> None:
        """
        Fit model with preprocessed data.

        Args:
            features (pd.DataFrame): preprocessed data.
            target (pd.DataFrame): target.
        """

        # safe copy
        features_ = features.copy()
        target_ = target.copy()

        n_y0 = int((target_.squeeze() == 0).sum())
        n_y1 = int((target_.squeeze() == 1).sum())
        # lightweight for deployments
        self._model = LogisticRegression(
            class_weight={1: n_y0 / len(target_), 0: n_y1 / len(target_)}
        )
        self._model.fit(features_[self._feature_cols], target)

    def predict(self, features: pd.DataFrame) -> List[int]:
        """
        Predict delays for new flights.

        Args:
            features (pd.DataFrame): preprocessed data.

        Returns:
            (List[int]): predicted targets.
        """

        if self._model is None:
            return [0] * len(features)
        features_ = features.copy()
        predicted_target = self._model.predict(features_[self._feature_cols])
        return [1 if y_pred > 0.5 else 0 for y_pred in predicted_target]
