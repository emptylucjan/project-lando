using System;
using System.IO;
using System.Reflection;
using System.Threading;
using InsERT.Moria.Sfera;
using InsERT.Mox.Product;
using InsERT.Moria.Dokumenty;
using InsERT.Moria.Dokumenty.Logistyka;
using InsERT.Moria.Asortymenty;
using InsERT.Moria.Klienci;
using Microsoft.Data.SqlClient;

class TestFZFlow
{
    static string connStr = "";

    static void Log(string s) => Console.WriteLine($"[{DateTime.Now:HH:mm:ss.fff}] {s}");
    static void Sep(string t) => Console.WriteLine($"\n======== {t} ========\n");

    static void Main(string[] args)
    {
        var dllDir    = @"C:\Users\julia\Downloads\nexoSDK_59.2.1.9164\Bin";
        var sferaDlls = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "sfera_dlls"));

        AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
        {
            var name = new AssemblyName(e.Name!).Name + ".dll";
            foreach (var dir in new[] { sferaDlls, AppContext.BaseDirectory, dllDir })
            {
                var p = Path.Combine(dir, name);
                if (File.Exists(p)) return Assembly.LoadFrom(p);
            }
            return null;
        };

        string dbServer   = @"192.168.7.6,1433";
        string dbName     = "Nexo_sport trade sp.z o.o.";
        string saPassword = "S2q0L2s024!";
        string opName     = "Łukasz Kondrat";
        string opPass     = "robocze";
        connStr = $"Server={dbServer};Database={dbName};User Id=sa;Password={saPassword};TrustServerCertificate=True;";

        Exception? threadEx = null;
        var t = new Thread(() =>
        {
            try { Run(dbServer, dbName, saPassword, opName, opPass, dllDir); }
            catch (Exception ex) { threadEx = ex; }
        });
        t.SetApartmentState(ApartmentState.STA);
        t.Start();
        t.Join();

        if (threadEx != null)
        {
            Console.WriteLine($"\n[BLAD] {threadEx.Message}\n{threadEx}");
            Environment.Exit(1);
        }
        Environment.Exit(0);
    }

    static void Run(string dbServer, string dbName, string saPassword, string opName, string opPass, string dllDir)
    {
        // Dane testowe
        string testInvNr   = "TEST-" + DateTime.Now.ToString("HHmmss");
        DateTime testInvDt = new DateTime(2026, 3, 31);   // data faktury Zalando

        Sep("1. POLACZENIE");
        var dane  = DanePolaczenia.Jawne(dbServer, dbName, false, "sa", saPassword, false, null, dllDir);
        var sfera = new MenedzerPolaczen().Polacz(dane, ProductId.Subiekt);
        bool ok = sfera.ZalogujOperatora(opName, opPass);
        Log($"Login: {ok}");
        if (!ok) throw new Exception("Login fail");

        // ─── 2. Zidentyfikuj Zalando SE ────────────────────────────────────────────
        Sep("2. ZNAJDZ ZALANDO SE");
        dynamic podmiotyMgr = sfera.PodajObiektTypu<IPodmioty>();
        dynamic? zalando = null;
        int zalandoId = 0;
        foreach (dynamic p in podmiotyMgr.Dane.Wszystkie())
        {
            string? naz = null;
            try { naz = (string)p.NazwaSkrocona; } catch { }
            if (naz != null && naz.Contains("Zalando"))
            {
                zalando = p;
                try { zalandoId = (int)p.Id; } catch { }
                Log($"  Znaleziono: '{naz}' Id={zalandoId}");
                break;
            }
        }
        if (zalando == null) throw new Exception("Nie znaleziono Zalando SE");

        // ─── 3. Utwórz PZ dla Zalando SE ────────────────────────────────────────────
        Sep("3. TWORZENIE PZ");
        dynamic pzMgr = sfera.PodajObiektTypu<IPrzyjeciaZewnetrzne>();
        dynamic pz = pzMgr.Utworz();

        // Podmiot
        try { pz.Dane.Podmiot = zalando; Log("  Podmiot=Zalando OK"); }
        catch (Exception ex) { Log($"  Podmiot ERR: {ex.Message}"); }

        // Numer zewnetrzny (numer faktury)
        try { pz.Dane.NumerZewnetrzny = testInvNr; Log($"  NumerZewnetrzny={testInvNr}"); }
        catch (Exception ex) { Log($"  NumerZewnetrzny ERR: {ex.Message}"); }

        // Data dokumentu
        try { pz.Dane.DataDokumentu = DateTime.Today; } catch { }

        // Dodaj 1 pozycje (pierwsza aktywna)
        dynamic asMgr = sfera.PodajObiektTypu<IAsortymenty>();
        string? produktSymbol = null;
        foreach (dynamic a in asMgr.Dane.Wszystkie())
        {
            try
            {
                if ((bool)a.CzyAktywny)
                {
                    produktSymbol = (string)a.Symbol;
                    Log($"  Produkt: {produktSymbol}");
                    break;
                }
            } catch { }
        }
        if (produktSymbol != null)
        {
            try
            {
                dynamic poz = pz.Pozycje.Dodaj(produktSymbol);
                try { poz.Ilosc = 1.0; } catch { }
                Log("  Pozycja dodana OK");
            }
            catch (Exception ex) { Log($"  Dodaj pozycja ERR: {ex.Message}"); }
        }

        try { pz.Przelicz(); Log("  Przelicz OK"); } catch (Exception ex) { Log($"  Przelicz ERR: {ex.Message}"); }

        bool pzMozna = false;
        try { pzMozna = (bool)pz.MoznaZapisac; } catch { }
        if (!pzMozna)
        {
            var b = new System.Text.StringBuilder();
            try { foreach (dynamic bl in pz.Bledy) b.Append(bl).Append("; "); } catch { }
            throw new Exception($"PZ MoznaZapisac=false: {b}");
        }

        bool pzZap = pz.Zapisz();
        string pzSyg = "";
        try { pzSyg = (string)pz.Dane.NumerWewnetrzny.PelnaSygnatura; } catch { }
        Log($"PZ Zapisana: {pzSyg} zapisano={pzZap}");
        try { ((IDisposable)pz).Dispose(); } catch { }

        // Pobierz Id z bazy
        int pzId = GetDocId(connStr, pzSyg);
        Log($"PZ Id w bazie: {pzId}");
        DbDump("PZ zaraz po zapisie (status=20 z SDK)", pzId);

        // ─── 4. Ustaw status na Odłożony (14) — symulacja stanu produkcyjnego ────────
        Sep("4. RESET STATUS PZ NA ODLOZONY (14)");
        SqlExec($"UPDATE ModelDanychContainer.Dokumenty SET StatusDokumentuId=14 WHERE Id={pzId}");
        DbDump("PZ po reset→14", pzId);

        // ─── 5. UpdateInvoice — NumerZewnetrzny + DataWydaniaWystawienia ─────────────
        Sep("5. UPDATE INVOICE (jak bot UpdateInvoice)");
        // NumerZewnetrzny
        SqlExec($"UPDATE ModelDanychContainer.Dokumenty SET NumerZewnetrzny='{testInvNr}' WHERE Id={pzId}");
        // DataWydaniaWystawienia = data oryginalu faktury
        SqlExec($"UPDATE ModelDanychContainer.Dokumenty SET DataWydaniaWystawienia='{testInvDt:yyyy-MM-dd}' WHERE Id={pzId}");
        // DataFakturyDostawcy (jesli istnieje jako kolumna)
        try { SqlExec($"UPDATE ModelDanychContainer.Dokumenty SET DataFakturyDostawcy='{testInvDt:yyyy-MM-dd}' WHERE Id={pzId}"); }
        catch { Log("  DataFakturyDostawcy — kolumna nie istnieje (OK)"); }
        DbDump("PZ po UpdateInvoice", pzId);

        // ─── 6. Zmień status 14→20 PRZED załadowaniem SDK ───────────────────────────
        Sep("6. STATUS 14→20 PRZED LADOWANIEM SDK");
        SqlExec($"UPDATE ModelDanychContainer.Dokumenty SET StatusDokumentuId=20 WHERE Id={pzId}");
        DbDump("PZ po→20 (przed SDK load)", pzId);

        // Załaduj PZ z SDK (teraz widzi status=20 w DB)
        dynamic pzMgr2 = sfera.PodajObiektTypu<IPrzyjeciaZewnetrzne>();
        dynamic? pzFound = null;
        foreach (dynamic pp in pzMgr2.Dane.Wszystkie())
            try { if ((int)pp.Id == pzId) { pzFound = pp; break; } } catch { }
        if (pzFound == null) throw new Exception($"SDK nie znalazlo PZ Id={pzId}");
        int sdkStat = -1;
        try { sdkStat = (int)pzFound.StatusDokumentu.Id; } catch { try { sdkStat = (int)pzFound.Status; } catch { } }
        Log($"PZ SDK: status={sdkStat} OK");

        // ─── 7. Utwórz FZ ────────────────────────────────────────────────────────────
        Sep("7. TWORZENIE FZ Z PZ");

        // Znajdz IDokumentyZakupu przez GetManager pattern z ReflectSfera
        dynamic? fzMgr = GetFzManager(sfera);
        if (fzMgr == null) throw new Exception("Nie znaleziono menedzera FZ (IDokumentyZakupu)");

        dynamic fz = fzMgr.UtworzFaktureZakupu();
        Log("FZ obiekt OK");

        var grup = new ParametryGrupowaniaDZ { MetodaGrupowaniaPozycji = MetodaGrupowaniaPozycji.BezKonsolidacji };
        // Uzyj runtime Array zamiast DokumentPZ[] — typ nie jest dostepny compile-time
        // Identyczny pattern co ReflectSfera: (DokumentPZ)(object)pzFound
        var pzType = pzFound.GetType();
        var pzArr2 = Array.CreateInstance(pzType, 1);
        pzArr2.SetValue(pzFound, 0);
        fz.WypelnijNaPodstawiePZ(pzArr2, pzFound, grup);
        Log("WypelnijNaPodstawiePZ OK");

        // Numer zewnetrzny = numer faktury dostawcy
        try { fz.Dane.NumerZewnetrzny = testInvNr; Log($"  FZ.NumerZewnetrzny={testInvNr}"); }
        catch (Exception ex) { Log($"  FZ.NumerZewnetrzny ERR: {ex.Message}"); }

        fz.Przelicz();
        Log("FZ Przelicz OK");

        // DUMP - jakie pola DateTime ma FZ?
        Log("Pola DateTime na FZ (DokumentDZ):");
        try
        {
            object daneFz = fz.Dane;
            foreach (var prop in daneFz.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
            {
                if (prop.PropertyType == typeof(DateTime) || prop.PropertyType == typeof(DateTime?))
                {
                    try { var v = prop.GetValue(daneFz); Log($"  {prop.Name} = {v}"); }
                    catch { Log($"  {prop.Name} = [read ERR]"); }
                }
            }
        } catch { }

        bool fzMozna = false;
        try { fzMozna = (bool)fz.MoznaZapisac; } catch { }
        Log($"FZ MoznaZapisac: {fzMozna}");

        bool fzZap = false;
        string fzErr = "";
        try { fzZap = fz.Zapisz(); }
        catch (Exception ex) { fzErr = ex.Message; }
        Log($"FZ Zapisz: {fzZap} {(string.IsNullOrEmpty(fzErr)?"":("ERR:"+fzErr))}");

        if (!fzZap)
        {
            var b = new System.Text.StringBuilder();
            try { foreach (dynamic bl in fz.Bledy) b.Append(bl).Append("; "); } catch { }
            // Przywroc PZ
            SqlExec($"UPDATE ModelDanychContainer.Dokumenty SET StatusDokumentuId=14 WHERE Id={pzId}");
            throw new Exception($"FZ nie zapisano. Bledy: {b}. ERR: {fzErr}");
        }

        string fzSyg = "";
        try { fzSyg = (string)fz.Dane.NumerWewnetrzny.PelnaSygnatura; } catch { }
        Log($"FZ zapisana: {fzSyg}");
        try { ((IDisposable)fz).Dispose(); } catch { }

        int fzId = GetDocId(connStr, fzSyg);
        Log($"FZ Id w bazie: {fzId}");

        // ─── 8. SQL: ustaw DataWydaniaWystawienia na FZ + przywroc PZ ────────────────
        Sep("8. POST-SAVE SQL UPDATE");

        // FZ: data oryginalu = data faktury dostawcy
        if (fzId > 0)
        {
            SqlExec($"UPDATE ModelDanychContainer.Dokumenty SET DataWydaniaWystawienia='{testInvDt:yyyy-MM-dd}' WHERE Id={fzId}");
            Log($"FZ DataWydaniaWystawienia → {testInvDt:yyyy-MM-dd}");
        }

        // PZ: przywroc status 14
        SqlExec($"UPDATE ModelDanychContainer.Dokumenty SET StatusDokumentuId=14 WHERE Id={pzId}");
        Log($"PZ status → 14 (przywrocony)");

        // ─── 9. Weryfikacja końcowa ─────────────────────────────────────────────────
        Sep("9. WERYFIKACJA KONCOWA Z BAZY");
        DbDump("PZ FINAL", pzId);
        DbDump("FZ FINAL", fzId);

        // ─── 10. Cleanup ─────────────────────────────────────────────────────────────
        Sep("10. CLEANUP");
        Log("Czy usunac testowe dokumenty? (t/n)");
        var ans = Console.ReadLine();
        if (ans?.Trim().ToLower() == "t")
        {
            DeleteDoc(fzId, fzSyg);
            DeleteDoc(pzId, pzSyg);
        }
        else
        {
            Log($"Pozostawiam: PZ={pzSyg} (Id={pzId}), FZ={fzSyg} (Id={fzId})");
            Log("Mozesz je recznie znalezc w Subiekcie i sprawdzic.");
        }

        sfera.Dispose();
        Log("\n=== TEST ZAKONCZONY SUKCESEM ===");
    }

    static dynamic? GetFzManager(Uchwyt sfera)
    {
        // Identyczny pattern jak GetManager() w ReflectSfera/Program.cs
        var sfType = sfera.GetType();
        foreach (var method in sfType.GetMethods())
        {
            if (method.Name != "PodajObiektTypu" || !method.IsGenericMethod) continue;
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                foreach (var candidate in new[] {
                    "InsERT.Moria.Faktury.IDokumentyZakupu",
                    "InsERT.Moria.Dokumenty.IDokumentyZakupu",
                    "InsERT.Moria.IDokumentyZakupu"
                })
                {
                    var t2 = asm.GetType(candidate);
                    if (t2 == null) continue;
                    try
                    {
                        var mgr = method.MakeGenericMethod(t2).Invoke(sfera, null);
                        if (mgr != null) { Console.WriteLine($"  IDokumentyZakupu: {t2.FullName}"); return (dynamic)mgr; }
                    }
                    catch { }
                }
            }
        }
        return null;
    }

    static int GetDocId(string connStr, string syg)
    {
        using var conn = new SqlConnection(connStr);
        conn.Open();
        using var cmd = new SqlCommand("SELECT Id FROM ModelDanychContainer.Dokumenty WHERE NumerWewnetrzny_PelnaSygnatura=@s", conn);
        cmd.Parameters.AddWithValue("@s", syg);
        var v = cmd.ExecuteScalar();
        return (v != null && v != DBNull.Value) ? Convert.ToInt32(v) : -1;
    }

    static void DbDump(string label, int docId)
    {
        if (docId <= 0) { Log($"[DB] {label}: brak Id"); return; }
        using var conn = new SqlConnection(connStr);
        conn.Open();
        using var cmd = new SqlCommand(@"
            SELECT Id, StatusDokumentuId, NumerWewnetrzny_PelnaSygnatura,
                   NumerZewnetrzny, DataWydaniaWystawienia, DataDokumentu
            FROM ModelDanychContainer.Dokumenty WHERE Id=@id", conn);
        cmd.Parameters.AddWithValue("@id", docId);
        using var r = cmd.ExecuteReader();
        if (r.Read())
            Log($"[DB] {label}: Status={r[1]} Syg={r[2]} NrZewn={NullStr(r,3)} DataWyd={DateStr(r,4)} DataDok={DateStr(r,5)}");
        else
            Log($"[DB] {label}: rek Id={docId} nie znaleziony");
    }

    static void SqlExec(string sql)
    {
        using var conn = new SqlConnection(connStr);
        conn.Open();
        using var cmd = new SqlCommand(sql, conn);
        int rows = cmd.ExecuteNonQuery();
        Log($"SQL ({rows} rows): {sql[..Math.Min(80, sql.Length)]}");
    }

    static void DeleteDoc(int docId, string label)
    {
        if (docId <= 0) return;
        Log($"Usuwam {label} (Id={docId})...");
        // UWAGA: w produkcyjnej bazie DELETE bezpośredni może naruszać FK.
        // Tutaj tylko próbujemy — jeśli fail, user usuwa ręcznie.
        foreach (var tbl in new[] {
            "ModelDanychContainer.DokumentyPozycje",
            "ModelDanychContainer.PozycjeDokumentow",
            "ModelDanychContainer.DokumentyPozycjeVat",
        })
        {
            try
            {
                using var conn = new SqlConnection(connStr);
                conn.Open();
                using var cmd = new SqlCommand($"DELETE FROM {tbl} WHERE DokumentId=@id OR Dokument_Id=@id", conn);
                cmd.Parameters.AddWithValue("@id", docId);
                cmd.ExecuteNonQuery();
            } catch { }
        }
        try
        {
            using var conn = new SqlConnection(connStr);
            conn.Open();
            using var cmd = new SqlCommand("DELETE FROM ModelDanychContainer.Dokumenty WHERE Id=@id", conn);
            cmd.Parameters.AddWithValue("@id", docId);
            int rows = cmd.ExecuteNonQuery();
            Log($"  Usunieto {rows} rek → {label}");
        }
        catch (Exception ex) { Log($"  DELETE ERR: {ex.Message} — usun recznie w Subiekcie"); }
    }

    static string NullStr(SqlDataReader r, int i) => r.IsDBNull(i) ? "NULL" : r.GetValue(i).ToString()!;
    static string DateStr(SqlDataReader r, int i) => r.IsDBNull(i) ? "NULL" : r.GetDateTime(i).ToString("yyyy-MM-dd");
}
