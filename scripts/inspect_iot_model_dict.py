from pathlib import Path
import joblib
import warnings

warnings.filterwarnings("ignore")

model_path = Path("models_external/iot_method_b_mlp_pipeline.pkl")
obj = joblib.load(model_path)

print("TYPE:", type(obj))

if isinstance(obj, dict):
    print("\nDICT KEYS:")
    for k, v in obj.items():
        print(f"- {k}: {type(v)}")

    print("\nDETAILED INSPECTION:")
    for k, v in obj.items():
        print("\n" + "="*80)
        print("KEY:", k)
        print("TYPE:", type(v))

        if isinstance(v, (list, tuple)):
            print("LEN:", len(v))
            print("VALUE:", v[:20])

        elif isinstance(v, dict):
            print("SUBKEYS:")
            for kk, vv in v.items():
                print(f"  - {kk}: {type(vv)}")

        else:
            attrs = [
                "feature_names_in_",
                "data_min_",
                "data_max_",
                "min_",
                "scale_",
                "mean_",
                "var_",
                "coefs_",
                "intercepts_",
                "hidden_layer_sizes",
                "activation",
                "out_activation_",
                "n_layers_",
                "n_outputs_"
            ]

            for attr in attrs:
                if hasattr(v, attr):
                    value = getattr(v, attr)
                    if attr in ["coefs_", "intercepts_"]:
                        print(attr, [x.shape for x in value])
                    else:
                        print(attr, value)

else:
    print("Object is not dict.")
    print("ATTRS:")
    for attr in dir(obj):
        if not attr.startswith("_"):
            print(attr)
