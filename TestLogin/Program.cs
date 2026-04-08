using System;
using System.IO;
using System.Reflection;
using System.Threading;
using InsERT.Moria.Sfera;
using InsERT.Mox.Product;

namespace TestLogin
{
    class Program
    {
        static void Main(string[] args)
        {
            var dllDir = @"C:\Users\julia\Downloads\nexoSDK_59.2.1.9164\Bin";
            // sfera_dlls/ is next to TestLogin/ — contains the actual licensed DLLs used by ReflectSfera
            var sferaDlls = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "sfera_dlls"));

            AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
            {
                var name = new AssemblyName(e.Name!).Name + ".dll";
                // 1. Try sfera_dlls (licensed, matches main project)
                var path1 = Path.Combine(sferaDlls, name);
                if (File.Exists(path1)) return Assembly.LoadFrom(path1);
                // 2. Try output dir (already copied by csproj)
                var path2 = Path.Combine(AppContext.BaseDirectory, name);
                if (File.Exists(path2)) return Assembly.LoadFrom(path2);
                // 3. Fallback: Downloads SDK
                var path3 = Path.Combine(dllDir, name);
                if (File.Exists(path3)) return Assembly.LoadFrom(path3);
                return null;
            };

            // ─── PARAMETRY ────────────────────────────────────────────
            string dbServer   = @"192.168.7.6,1433";
            string dbName     = "Nexo_sport trade sp.z o.o.";
            string saPassword = "S2q0L2s024!";
            string opName     = "Łukasz Kondrat";
            string opPass     = "robocze";
            // ──────────────────────────────────────────────────────────

            Console.WriteLine($"[TEST] Serwer  : {dbServer}");
            Console.WriteLine($"[TEST] Baza    : {dbName}");
            Console.WriteLine($"[TEST] Operator: {opName}");
            Console.WriteLine($"[TEST] Haslo op: {opPass}");
            Console.WriteLine();

            Exception? threadEx = null;
            bool loginOk = false;

            var t = new Thread(() =>
            {
                try
                {
                    Console.WriteLine("[TEST] Lacze ze Sfera...");
                    var dane = DanePolaczenia.Jawne(
                        dbServer, dbName,
                        false, "sa", saPassword,
                        false, null, dllDir);

                    var mgr = new MenedzerPolaczen();
                    Uchwyt sfera = mgr.Polacz(dane, ProductId.Subiekt);
                    Console.WriteLine("[TEST] Polaczono ze Sfera. Proba logowania operatora...");

                    loginOk = sfera.ZalogujOperatora(opName, opPass);
                    Console.WriteLine($"[TEST] ZalogujOperatora(\"{opName}\", \"{opPass}\") => {loginOk}");

                    if (!loginOk)
                    {
                        Console.WriteLine("[TEST] --- Sprawdzam warianty nazwy operatora ---");
                        string[] nameVariants = {
                            "Lukasz Kondrat",
                            "lukasz kondrat",
                            "ŁUKASZ KONDRAT",
                        };
                        foreach (var v in nameVariants)
                        {
                            bool r = sfera.ZalogujOperatora(v, opPass);
                            Console.WriteLine($"[TEST]   '{v}' / '{opPass}' => {r}");
                        }

                        Console.WriteLine("[TEST] --- Sprawdzam warianty hasla ---");
                        string[] passVariants = { "", "Robocze", "ROBOCZE", "robocze1", "test", "nexo", "admin" };
                        foreach (var p in passVariants)
                        {
                            bool r = sfera.ZalogujOperatora(opName, p);
                            Console.WriteLine($"[TEST]   '{opName}' / '{p}' => {r}");
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
                Console.WriteLine($"\n[BLAD] Wyjatek:\n{threadEx}");
                Environment.Exit(1);
            }

            Console.WriteLine($"\n[WYNIK] Login operatora: {(loginOk ? "OK - SUKCES" : "NIEPOWODZENIE")}");
            Environment.Exit(loginOk ? 0 : 2);
        }
    }
}
