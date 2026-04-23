

# Definitions  

Because both models have almost the same results (DS Observation), I decided to deploy logistic regression because it is more lightweight compared with XGBoost in terms of training and deployment, uses lighter libraries, and results in lower final memory consumption for the service.


# Bugs detected 

1) The `test_model_fit` test in `test_model.py` contains a bug: although the execution appears agnostic, the evaluation metrics are computed on a dataset that was also used for training. In effect, the training data is not properly separated, as the model is trained on the entire dataset and then tested on a subset of that same data. The fix was to activate proper data splitting so that training and testing are performed on distinct datasets.


Old test: 

```python
def test_model_fit(self):
    features, target = self.model.preprocess(data=self.data, target_column="delay")

    _, features_validation, _, target_validation = train_test_split(
        features, target, test_size=0.33, random_state=42
    )

    self.model.fit(features=features, target=target)

    predicted_target = self.model._model.predict(features_validation)

    report = classification_report(
        target_validation, predicted_target, output_dict=True
    )

    assert report["0"]["recall"] < 0.60
    assert report["0"]["f1-score"] < 0.70
    assert report["1"]["recall"] > 0.60
    assert report["1"]["f1-score"] > 0.30
```

New test: 

```python
def test_model_fit(self):
    features, target = self.model.preprocess(data=self.data, target_column="delay")

    features_training, features_validation, target_training, target_validation = (
        train_test_split(features, target, test_size=0.33, random_state=42)
    )

    self.model.fit(features=features_training, target=target_training)
    predicted_target = self.model._model.predict(features_validation)
    report = classification_report(
        target_validation, predicted_target, output_dict=True
    )

    assert report["0"]["recall"] < 0.60
    assert report["0"]["f1-score"] < 0.70
    assert report["1"]["recall"] > 0.60
    assert report["1"]["f1-score"] > 0.30
```

