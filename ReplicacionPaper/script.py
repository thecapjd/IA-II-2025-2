# ==============================================================================
# SCRIPT COMPLETO PARA REPLICAR EL EXPERIMENTO (VERSIÓN FINAL MEJORADA)
# ==============================================================================

# --- IMPORTACIONES NECESARIAS ---
import pandas as pd
import numpy as np
from sklearn.feature_selection import VarianceThreshold
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import KBinsDiscretizer # <<< IMPORTACIÓN CLAVE
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score, classification_report
import wittgenstein as lw
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)


# ------------------------------------------------------------------------------
# <<< CLASE OneR ACTUALIZADA Y MEJORADA >>>
# Esta nueva versión utiliza una técnica de binning (discretización) superior,
# que es crucial para que el algoritmo funcione correctamente.
# ------------------------------------------------------------------------------
class AdvancedOneR:
    def __init__(self, n_bins=10):
        self.n_bins = n_bins
        self.best_feature_ = None
        self.best_discretizer_ = None
        self.rules_ = {}
        self.global_majority_class_ = None

    def fit(self, X, y):
        self.global_majority_class_ = y.mode()[0]
        min_error = float('inf')

        for feature in X.columns:
            # Usamos KBinsDiscretizer con estrategia 'quantile'
            # Esto crea bins con un número similar de muestras, ideal para clases desbalanceadas
            discretizer = KBinsDiscretizer(n_bins=self.n_bins, encode='ordinal', strategy='quantile', subsample=None)
            
            # Preparamos los datos para el discretizador (necesita un array 2D)
            feature_values = X[[feature]].to_numpy()
            
            try:
                discretized_feature = discretizer.fit_transform(feature_values).flatten()
            except ValueError:
                # Si falla (ej. por no tener suficientes valores únicos), saltamos esta característica
                continue
                
            rules, error = {}, 0
            # np.unique() para obtener todos los posibles bins (0, 1, 2, ...)
            for bin_label in np.unique(discretized_feature):
                mask = (discretized_feature == bin_label)
                most_common_class = y[mask].mode()[0]
                rules[bin_label] = most_common_class
                error += np.sum(y[mask] != most_common_class)
            
            if error < min_error:
                min_error = error
                self.best_feature_ = feature
                self.rules_ = rules
                self.best_discretizer_ = discretizer # Guardamos el discretizador entrenado
        return self

    def predict(self, X):
        if self.best_feature_ is None: raise RuntimeError("El modelo debe ser entrenado.")
        
        feature_values = X[[self.best_feature_]].to_numpy()
        # Usamos el discretizador ya entrenado para transformar los nuevos datos
        discretized_feature = self.best_discretizer_.transform(feature_values).flatten()
        
        # Mapeamos los bins a las predicciones de clase
        predictions = pd.Series(discretized_feature).map(self.rules_).fillna(self.global_majority_class_)
        return predictions.to_numpy().astype(int)

# --- PASO 1: CARGA DE DATOS ---
print("--- Paso 1: Cargando y preparando el dataset ---")
try:
    df = pd.read_csv('CICIDS2017.csv', low_memory=False)
except FileNotFoundError:
    print("\nERROR: Archivo 'CICIDS2017.csv' no encontrado.")
    exit()

df.columns = df.columns.str.strip()
df_filtered = df[df['Label'].isin(['BENIGN', 'PortScan'])].copy()
df_filtered['Label'] = df_filtered['Label'].map({'BENIGN': 0, 'PortScan': 1})
df_filtered.replace([np.inf, -np.inf], np.nan, inplace=True)
df_filtered.dropna(inplace=True)
X = df_filtered.drop('Label', axis=1)
y = df_filtered['Label']
print(f"Dataset listo. Forma: {df_filtered.shape}\n")


# --- PASO 2: SELECCIÓN DE CARACTERÍSTICAS ---
print("--- Paso 2: Realizando selección de características ---")
X_numeric = X.select_dtypes(include=np.number)
selector_var = VarianceThreshold(threshold=3.4)
X_high_variance_np = selector_var.fit_transform(X_numeric)
feature_names_hv = X_numeric.columns[selector_var.get_support()]
X_high_variance = pd.DataFrame(X_high_variance_np, columns=feature_names_hv, index=X_numeric.index)
print(f"Características después de filtro de varianza: {X_high_variance.shape[1]}")
features_from_paper = ['PSH Flag Count', 'Avg Bwd Segment Size', 'Bwd Packet Length Mean', 'Bwd Packet Length Min', 'Init_Win_bytes_backward', 'Subflow Bwd Bytes', 'Total Length of Bwd Packets', 'min_seg_size_forward', 'Bwd Packet Length Max', 'Packet Length Mean', 'Average Packet Size', 'act_data_pkt_fwd', 'Max Packet Length']
available_features = [feat for feat in features_from_paper if feat in X_high_variance.columns]
X_final = X_high_variance[available_features]
print(f"Características seleccionadas según el paper: {len(available_features)}\n")


# --- PASO 3: DIVISIÓN DE DATOS ---
print("--- Paso 3: Dividiendo los datos en entrenamiento y prueba (50/50) ---")
X_train_orig, X_test_orig, y_train, y_test = train_test_split(
    X_final, y, test_size=0.5, random_state=42, stratify=y
)
print(f"División de datos completada.\n")


# --- PASO 4: ENTRENAMIENTO DE MODELOS ---
print("--- Paso 4: Entrenando los modelos ---")
# NOTA: Los modelos JRip y OneR no necesitan normalización (scaling)
# ya que son basados en reglas y árboles, así que usamos los datos originales.
print("Entrenando modelo JRip...")
jrip_model = lw.RIPPER(random_state=42)
jrip_model.fit(X_train_orig, y_train)

print("Entrenando modelo OneR...")
oner_model = AdvancedOneR(n_bins=10)
oner_model.fit(X_train_orig, y_train)
print("Modelos entrenados.\n")


# --- PASO 5: EVALUACIÓN ---
print("--- Paso 5: Evaluando los modelos en el set de prueba ---\n")
y_pred_jrip = jrip_model.predict(X_test_orig)
print("--- Resultados de Evaluación: JRip ---")
print(classification_report(y_test, y_pred_jrip, target_names=['Benign', 'PortScan'], digits=4))

y_pred_oner = oner_model.predict(X_test_orig)
print("\n--- Resultados de Evaluación: OneR ---")
print(classification_report(y_test, y_pred_oner, target_names=['Benign', 'PortScan'], digits=4))


# --- Comparación Final ---
print("\n--- Comparación de Resultados vs. Artículo ---")
accuracy_jrip, recall_jrip, precision_jrip, f1_jrip = accuracy_score(y_test, y_pred_jrip), recall_score(y_test, y_pred_jrip), precision_score(y_test, y_pred_jrip), f1_score(y_test, y_pred_jrip)
accuracy_oner, recall_oner, precision_oner, f1_oner = accuracy_score(y_test, y_pred_oner), recall_score(y_test, y_pred_oner), precision_score(y_test, y_pred_oner), f1_score(y_test, y_pred_oner)
print("Métrica      | JRip (Obtenido) | JRip (Artículo) | OneR (Obtenido) | OneR (Artículo)")
print("-------------|-----------------|-----------------|-----------------|----------------")
print(f"Accuracy     | {accuracy_jrip:.4f}        | ~0.9984         | {accuracy_oner:.4f}       | ~0.9956")
print(f"Recall       | {recall_jrip:.4f}        | ~0.9980         | {recall_oner:.4f}       | ~0.9960")
print(f"Precision    | {precision_jrip:.4f}        | ~0.9980         | {precision_oner:.4f}       | ~0.9940")
print(f"F-Measure    | {f1_jrip:.4f}        | ~0.9980         | {f1_oner:.4f}       | ~0.9950")