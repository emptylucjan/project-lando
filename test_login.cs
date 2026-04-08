// Izolowany test logowania operatora Sfera
// Uruchom: dotnet-script test_login.cs
// Lub skompiluj: csc /r:... test_login.cs
// Wymaga tych samych DLL co ReflectSfera

using System;
using System.IO;
using System.Reflection;
using System.Threading;

var dllDir = @"C:\Users\julia\Downloads\nexoSDK_59.2.1.9164\Bin";

AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
{
    var name = new AssemblyName(e.Name).Name + ".dll";
    var path = Path.Combine(dllDir, name);
    if (File.Exists(path)) return Assembly.LoadFrom(path);
    return null;
};

// ─── PARAMETRY ────────────────────────────────────────────────
string dbServer   = @"192.168.7.6,1433";
string dbName     = "Nexo_sport trade sp.z o.o.";
string saPassword = "S2q0L2s024!";
string opName     = "Łukasz Kondrat";
string opPass     = "robocze";
// ──────────────────────────────────────────────────────────────

Console.WriteLine($"[TEST] Serwer  : {dbServer}");
Console.WriteLine($"[TEST] Baza    : {dbName}");
Console.WriteLine($"[TEST] Operator: {opName}");
Console.WriteLine($"[TEST] Hasło op: {opPass}");
Console.WriteLine();

Exception? threadEx = null;
bool loginOk = false;

var t = new Thread(() =>
{
    try
    {
        Console.WriteLine("[TEST] Łączę ze Sferą...");
        var dane = InsERT.Moria.Sfera.DanePolaczenia.Jawne(
            dbServer, dbName,
            false, "sa", saPassword,
            false, null, dllDir);

        var mgr = new InsERT.Moria.Sfera.MenedzerPolaczen();
        var sfera = mgr.Polacz(dane, InsERT.Mox.Product.ProductId.Subiekt);
        Console.WriteLine("[TEST] Połączono ze Sferą. Próba logowania operatora...");

        loginOk = sfera.ZalogujOperatora(opName, opPass);
        Console.WriteLine($"[TEST] ZalogujOperatora(\"{opName}\", \"{opPass}\") => {loginOk}");

        if (!loginOk)
        {
            // Spróbuj kilka wariantów nazwy
            string[] variants = {
                "Lukasz Kondrat",
                "lukasz kondrat",
                "ŁUKASZ KONDRAT",
                "Łukasz kondrat",
            };
            foreach (var v in variants)
            {
                bool r = sfera.ZalogujOperatora(v, opPass);
                Console.WriteLine($"[TEST]   wariant '{v}' => {r}");
                if (r) break;
            }

            // Spróbuj różnych haseł
            string[] passes = { "", "Robocze", "ROBOCZE", "robocze1", "admin", "nexo" };
            foreach (var p in passes)
            {
                bool r = sfera.ZalogujOperatora(opName, p);
                Console.WriteLine($"[TEST]   hasło '{p}' => {r}");
                if (r) break;
            }
        }

        sfera.Dispose();
    }
    catch (Exception ex)
    {
        threadEx = ex;
    }
});
t.SetApartmentState(ApartmentState.STA);
t.Start();
t.Join();

if (threadEx != null)
{
    Console.WriteLine($"\n[BŁĄD] Wyjątek podczas testu:\n{threadEx}");
    Environment.Exit(1);
}

Console.WriteLine($"\n[WYNIK] Login operatora: {(loginOk ? "✅ SUKCES" : "❌ NIEPOWODZENIE")}");
Environment.Exit(loginOk ? 0 : 2);
