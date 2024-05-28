import numpy as np

def mean_absolute_error(y_true, y_pred):
    """
    Calculate Mean Absolute Error (MAE)
    :param y_true: Array of true ratings
    :param y_pred: Array of predicted ratings
    :return: MAE value
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.mean(np.abs(y_true - y_pred))

def root_mean_squared_error(y_true, y_pred):
    """
    Calculate Root Mean Squared Error (RMSE)
    :param y_true: Array of true ratings
    :param y_pred: Array of predicted ratings
    :return: RMSE value
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.sqrt(np.mean((y_true - y_pred) ** 2))

def precision_at_k(y_true, y_pred, k):
    """
    Calculate Precision at K
    :param y_true: Array of true item IDs
    :param y_pred: Array of predicted item IDs
    :param k: Number of top recommendations to consider
    :return: Precision at K value
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)[:k]
    return len(set(y_true) & set(y_pred)) / float(k)

def recall_at_k(y_true, y_pred, k):
    """
    Calculate Recall at K
    :param y_true: Array of true item IDs
    :param y_pred: Array of predicted item IDs
    :param k: Number of top recommendations to consider
    :return: Recall at K value
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)[:k]
    return len(set(y_true) & set(y_pred)) / float(len(y_true))
import numpy as np

def mean_absolute_error(y_true, y_pred):
    """
    Calculate Mean Absolute Error (MAE)
    :param y_true: Array of true ratings
    :param y_pred: Array of predicted ratings
    :return: MAE value
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.mean(np.abs(y_true - y_pred))

def root_mean_squared_error(y_true, y_pred):
    """
    Calculate Root Mean Squared Error (RMSE)
    :param y_true: Array of true ratings
    :param y_pred: Array of predicted ratings
    :return: RMSE value
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return np.sqrt(np.mean((y_true - y_pred) ** 2))

def precision_at_k(y_true, y_pred, k):
    """
    Calculate Precision at K
    :param y_true: Array of true item IDs
    :param y_pred: Array of predicted item IDs
    :param k: Number of top recommendations to consider
    :return: Precision at K value
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)[:k]
    return len(set(y_true) & set(y_pred)) / float(k)

def recall_at_k(y_true, y_pred, k):
    """
    Calculate Recall at K
    :param y_true: Array of true item IDs
    :param y_pred: Array of predicted item IDs
    :param k: Number of top recommendations to consider
    :return: Recall at K value
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)[:k]
    return len(set(y_true) & set(y_pred)) / float(len(y_true))