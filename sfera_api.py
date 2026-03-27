import json
import subprocess
import os
import tempfile

# Ścieżka do zbudowanego programu ReflectSfera.exe
SFERA_EXE = os.path.join(os.path.dirname(__file__), "ReflectSfera", "bin", "Release", "net8.0-windows", "ReflectSfera.exe")

def run_sfera_action(action: str, payload: dict, sfera_password: str = "") -> dict:
    if not os.path.exists(SFERA_EXE):
        raise FileNotFoundError(f"Sfera CLI nie istnieje: {SFERA_EXE}. Uruchom 'dotnet build' w folderze ReflectSfera.")

    req = {
        "Action": action,
        "DbName": "Nexo_eleat teesty kurwa",
        "DbServer": ".\\INSERTNEXO",
        "SferaPassword": sfera_password
    }
    
    if action == "EnsureProducts":
        # Wersja list() lub pojedynczy slownik
        req["EnsureProducts"] = payload if isinstance(payload, list) else [payload]
    elif action == "CreatePZ":
        req["PzData"] = payload
    else:
        raise ValueError("Unknown action: " + action)
        
    req_path = os.path.join(os.path.dirname(__file__), f"sfera_req_{action}.json")
    with open(req_path, "w", encoding="utf-8") as f:
        json.dump(req, f, ensure_ascii=False)
        
    try:
        result = subprocess.run([SFERA_EXE, req_path], capture_output=True)
        out = result.stdout.decode("utf-8", errors="replace").strip()
        err = result.stderr.decode("utf-8", errors="replace").strip()
        
        if result.returncode != 0:
            print(f"[sfera_api] BŁĄD PROCESU: {err}")
            return {"Success": False, "Message": err}

        # Ostatnia poprawna linia JSON to odpowiedź
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith("{") and "Success" in line:
                try:
                    return json.loads(line)
                except Exception as e:
                    pass
        print(f"[sfera_api] RAW OUTPUT:\n{out}")
        return {"Success": False, "Message": "Zła odpowiedź z ReflectSfera.exe", "Raw": out}
    except Exception as e:
        return {"Success": False, "Message": str(e)}
    # finally:
        # try:
        #     os.remove(req_path)
        # except:
        #     pass
