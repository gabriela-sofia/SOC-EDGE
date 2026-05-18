from pathlib import Path
import joblib

model_path = Path("models_external/iot_method_b_mlp_pipeline.pkl")

print("MODEL EXISTS:", model_path.exists())
print("MODEL PATH:", model_path.resolve())

if not model_path.exists():
    raise SystemExit("ERRO: modelo não encontrado.")

pipe = joblib.load(model_path)

print("\nTYPE:", type(pipe))

if hasattr(pipe, "steps"):
    print("\nPIPELINE STEPS:")
    for name, step in pipe.steps:
        print(" -", name, ":", type(step))

    print("\nFEATURE_NAMES_IN:")
    found_features = False

    if hasattr(pipe, "feature_names_in_"):
        print("pipeline:", list(pipe.feature_names_in_))
        found_features = True

    for name, step in pipe.steps:
        if hasattr(step, "feature_names_in_"):
            print(name + ":", list(step.feature_names_in_))
            found_features = True

    if not found_features:
        print("Nenhum feature_names_in_ encontrado no pipeline/steps.")

    print("\nSCALER/TRANSFORMER PARAMS:")
    for name, step in pipe.steps:
        printed = False
        if hasattr(step, "mean_"):
            print(name, "mean_:", step.mean_)
            printed = True
        if hasattr(step, "scale_"):
            print(name, "scale_:", step.scale_)
            printed = True
        if hasattr(step, "data_min_"):
            print(name, "data_min_:", step.data_min_)
            printed = True
        if hasattr(step, "data_max_"):
            print(name, "data_max_:", step.data_max_)
            printed = True
        if printed:
            print()

    print("\nMLP PARAMS:")
    found_mlp = False
    for name, step in pipe.steps:
        if hasattr(step, "coefs_"):
            found_mlp = True
            print("MLP step:", name)
            print("hidden_layer_sizes:", getattr(step, "hidden_layer_sizes", None))
            print("activation:", getattr(step, "activation", None))
            print("out_activation_:", getattr(step, "out_activation_", None))
            print("n_layers_:", getattr(step, "n_layers_", None))
            print("n_outputs_:", getattr(step, "n_outputs_", None))
            print("coefs shapes:", [w.shape for w in step.coefs_])
            print("intercepts shapes:", [b.shape for b in step.intercepts_])

    if not found_mlp:
        print("Nenhum step com coefs_ encontrado.")

else:
    print("\nNot a sklearn Pipeline.")
    print("FEATURE_NAMES_IN:", getattr(pipe, "feature_names_in_", None))
    if hasattr(pipe, "coefs_"):
        print("hidden_layer_sizes:", getattr(pipe, "hidden_layer_sizes", None))
        print("activation:", getattr(pipe, "activation", None))
        print("coefs shapes:", [w.shape for w in pipe.coefs_])
