using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.SqlClient;

using InsERT.Moria.Sfera;
using InsERT.Moria.ModelDanych;
using InsERT.Moria.Dokumenty.Logistyka;
using InsERT.Moria.Asortymenty;
using InsERT.Moria.Klienci;
using InsERT.Moria.Waluty;

namespace ReflectSfera
{
    public class CliRequest
    {
        public string Action { get; set; } = "";
        public string DbName { get; set; } = "Nexo_eleat teesty kurwa";
        public string DbServer { get; set; } = @".\INSERTNEXO";
        public string SferaPassword { get; set; } = "";
        
        public List<EnsureProductRequest>? EnsureProducts { get; set; }
        public PzRequest? PzData { get; set; }
        public UpdateTrackingRequest? UpdateTracking { get; set; }
        public UpdateInvoiceRequest? UpdateInvoice { get; set; }
        public AcceptPzRequest? AcceptPz { get; set; }
        public FzRequest? FzData { get; set; }
        public ZkRequest? ZkData { get; set; }
        public UpdatePzRequest? UpdatePzData { get; set; }
    }

    public class EnsureProductRequest
    {
        public string? SKU { get; set; }
        public string? EAN { get; set; }
        public string? Size { get; set; }
        public string? Brand { get; set; }
        public string? ModelName { get; set; }
    }

    public class PzRequest
    {
        public string? DostawcaNip { get; set; }
        public string? DostawcaEmail { get; set; }
        public string? Uwagi { get; set; }
        public string? NumerFakturyDostawcy { get; set; }
        public string? NumerZamowieniaZalando { get; set; }
        public List<PzFzItem> Items { get; set; } = new();
    }

    public class PzFzItem
    {
        public string? Symbol { get; set; }
        public string? EAN { get; set; }
        public decimal Quantity { get; set; }
        public decimal? CenaZakupu { get; set; }
    }

    public class UpdateTrackingRequest
    {
        public string? OrderName { get; set; }
        public string? Tracking { get; set; }
    }

    public class UpdateInvoiceRequest
    {
        public string? OrderName { get; set; }
        public string? InvoiceNumber { get; set; }
        public string? InvoiceDate { get; set; }
        public string? Tracking { get; set; }
    }

    public class AcceptPzRequest
    {
        public string? Tracking { get; set; }
    }

    public class FzRequest
    {
        public string? DostawcaNip { get; set; }
        public string? NumerFakturyDostawcy { get; set; }
        public string? InvoiceDate { get; set; }
        public string? OrderName { get; set; }
        public List<PzFzItem> Items { get; set; } = new();
    }

    public class CliResponse
    {
        public bool Success { get; set; }
        public string? Message { get; set; }
        public string? DocumentNumber { get; set; }
        public string? Sygnatura { get; set; }
        public Dictionary<string, bool>? EnsureResults { get; set; }
    }

    public class UpdatePzRequest
    {
        public string? PzSygnatura { get; set; }
        public List<UpdatePzItem> Items { get; set; } = new();
    }

    public class UpdatePzItem
    {
        public string? EAN { get; set; }
        public int QtyToSubtract { get; set; }
    }

    public class ZkRequest
    {
        public string CustomerName { get; set; } = "zmien_nazwe";
        public string Currency { get; set; } = "EUR";
        public string? TicketName { get; set; }
        public List<ZkItem> Items { get; set; } = new();
    }

    public class ZkItem
    {
        public string? EAN { get; set; }
        public string? Symbol { get; set; }
        public decimal Quantity { get; set; }
    }

    class Program
    {
        static async Task Main(string[] args)
        {
            if (args.Length == 0)
            {
                Console.WriteLine("{\"Success\":false,\"Message\":\"Brak pliku wejsciowego\"}");
                return;
            }

            // ObejĹ›cie problemu Ĺ‚adowania DLL Sfery przez STA Thread
            var dllDir = @"C:\Users\lukko\Desktop\MODULKURIERSKI_PRODUKCJA";
            AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
            {
                var name = new AssemblyName(e.Name).Name + ".dll";
                var path = Path.Combine(dllDir, name);
                if (File.Exists(path)) return Assembly.LoadFrom(path);
                return null;
            };

            try
            {
                string json = await File.ReadAllTextAsync(args[0]);
                var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
                var req = JsonSerializer.Deserialize<CliRequest>(json, options);

                if (req == null) throw new Exception("Pusty request JSON");

                CliResponse res = new CliResponse();

                var tcs = new TaskCompletionSource<CliResponse>();
                var thread = new Thread(() =>
                {
                    try
                    {
                        var result = ProcessAction(req);
                        tcs.SetResult(result);
                    }
                    catch (Exception ex)
                    {
                        tcs.SetException(ex);
                    }
                });
                thread.SetApartmentState(ApartmentState.STA);
                thread.Start();

                res = await tcs.Task;
                Console.WriteLine(JsonSerializer.Serialize(res));
            }
            catch (Exception ex)
            {
                var err = new CliResponse { Success = false, Message = ex.ToString() };
                Console.WriteLine(JsonSerializer.Serialize(err));
            }
        }

        static CliResponse ProcessAction(CliRequest req)
        {
            var dllPath = @"C:\Users\lukko\Desktop\MODULKURIERSKI_PRODUKCJA";
            
            var dane = InsERT.Moria.Sfera.DanePolaczenia.Jawne(req.DbServer, req.DbName, false, "sa", req.SferaPassword, false, null, dllPath);
            var mgr = new InsERT.Moria.Sfera.MenedzerPolaczen();

            Uchwyt sfera = mgr.Polacz(dane, InsERT.Mox.Product.ProductId.Subiekt);
            if (!sfera.ZalogujOperatora("Aleksander PIsiecki", "robocze")) {
                throw new Exception("BĹ‚Ä…d logowania operatora Aleksander PIsiecki");
            }

            try
            {
                string connStr = $"Server={req.DbServer};Database={req.DbName};User Id=sa;Password={req.SferaPassword};TrustServerCertificate=True;";

                if (req.Action == "EnsureProducts" && req.EnsureProducts != null)
                {
                    var results = new Dictionary<string, bool>();
                    foreach (var pReq in req.EnsureProducts)
                    {
                        string key = $"{pReq.SKU}-{pReq.Size}";
                        bool created = EnsureProductExists(sfera, pReq, connStr);
                        results[key] = created;
                    }
                    return new CliResponse { Success = true, EnsureResults = results };
                }
                else if (req.Action == "CreatePZ" && req.PzData != null)
                {
                    string docNum = CreatePZ(sfera, req.PzData, connStr);
                    return new CliResponse { Success = true, DocumentNumber = docNum };
                }
                else if (req.Action == "UpdateTracking" && req.UpdateTracking != null)
                {
                    return UpdateTracking(connStr, req.UpdateTracking);
                }
                else if (req.Action == "UpdateInvoice" && req.UpdateInvoice != null)
                {
                    return UpdateInvoice(sfera, connStr, req.UpdateInvoice);
                }
                else if (req.Action == "AcceptPZ" && req.AcceptPz != null)
                {
                    return AcceptPZ(sfera, connStr, req.AcceptPz);
                }
                else if (req.Action == "CreateFZ" && req.FzData != null)
                {
                    string docNum = CreateFZ(sfera, connStr, req.FzData);
                    return new CliResponse { Success = true, DocumentNumber = docNum };
                }
                else if (req.Action == "CreateZK" && req.ZkData != null)
                {
                    string docNum = CreateZK(sfera, req.ZkData);
                    return new CliResponse { Success = true, DocumentNumber = docNum };
                }
                else if (req.Action == "UpdatePzPositions" && req.UpdatePzData != null)
                {
                    var msg = UpdatePzPositions(sfera, connStr, req.UpdatePzData);
                    return new CliResponse { Success = true, Message = msg };
                }
                else
                {
                    return new CliResponse { Success = false, Message = "Nieznana akcja lub brak danych" };
                }
            }
            finally
            {
                sfera.Dispose();
            }
        }

        static dynamic? GetManager(Uchwyt sfera, string interfaceSimpleName)
        {
            // 1. Szukaj w juĹĽ zaĹ‚adowanych assembly
            var t = AppDomain.CurrentDomain.GetAssemblies()
                .SelectMany(asm => { try { return asm.GetTypes(); } catch { return Array.Empty<Type>(); } })
                .FirstOrDefault(t => t.IsInterface && t.Name == interfaceSimpleName);

            // 2. Fallback: skanuj produkcyjne DLL InsERT.Moria*
            if (t == null)
            {
                var dllDir = @"C:\Users\lukko\Desktop\MODULKURIERSKI_PRODUKCJA";
                if (Directory.Exists(dllDir))
                {
                    foreach (var dll in Directory.GetFiles(dllDir, "InsERT.Moria*.dll"))
                    {
                        try
                        {
                            var asm = Assembly.LoadFrom(dll);
                            t = asm.GetTypes().FirstOrDefault(x => x.IsInterface && x.Name == interfaceSimpleName);
                            if (t != null) break;
                        }
                        catch { }
                    }
                }
            }

            if (t == null) return null;
            try
            {
                var method = (sfera as object).GetType().GetMethod("PodajObiektTypu")?.MakeGenericMethod(t);
                if (method != null) return method.Invoke(sfera, null);
            }
            catch { }
            return null;
        }

        static bool EnsureProductExists(Uchwyt sfera, EnsureProductRequest req, string connStr)
        {
            string expectedSymbol;
            if (!string.IsNullOrWhiteSpace(req.SKU) && !string.IsNullOrWhiteSpace(req.Size))
                expectedSymbol = $"{req.SKU}-{req.Size}".Replace(",", ".").Replace(" ", "").Replace("/", "-");
            else if (!string.IsNullOrWhiteSpace(req.SKU))
                expectedSymbol = req.SKU.Replace(" ", "");
            else if (!string.IsNullOrWhiteSpace(req.EAN))
                expectedSymbol = req.EAN.Length > 20 ? req.EAN.Substring(0, 20) : req.EAN;
            else
                expectedSymbol = "PROD-" + Guid.NewGuid().ToString("N").Substring(0, 8);

            // UĹĽyj ModelName z Python (juĹĽ prawidĹ‚owo sformatowane: 'Nike Sportswear HV4517-100 Â· 43')
            // JeĹ›li brak ModelName, buduj z dostÄ™pnych czÄ™Ĺ›ci
            string nazwaSubiekt;
            if (!string.IsNullOrWhiteSpace(req.ModelName))
                nazwaSubiekt = req.ModelName;
            else {
                var nameParts = new List<string>();
                if (!string.IsNullOrWhiteSpace(req.Brand)) nameParts.Add(req.Brand);
                if (!string.IsNullOrWhiteSpace(req.SKU)) nameParts.Add(req.SKU);
                nazwaSubiekt = string.Join(" ", nameParts);
                if (!string.IsNullOrWhiteSpace(req.Size))
                    nazwaSubiekt += (nazwaSubiekt.Length > 0 ? " \u00b7 " : "") + req.Size;
                if (string.IsNullOrWhiteSpace(nazwaSubiekt)) nazwaSubiekt = req.EAN ?? "Produkt";
            }
            if (nazwaSubiekt.Length > 50) nazwaSubiekt = nazwaSubiekt.Substring(0, 50);

            string opisSubiekt = $"{req.Brand} {req.SKU} {req.Size}".Trim();

            if (expectedSymbol.Length > 20) expectedSymbol = expectedSymbol.Substring(0, 20);

            // 1. Zawsze szukaj po EAN â€” to jest gĹ‚Ăłwny klucz produktu
            if (!string.IsNullOrWhiteSpace(req.EAN))
            {
                using var conn = new SqlConnection(connStr);
                conn.Open();
                var sql = @"SELECT TOP 1 a.Symbol FROM ModelDanychContainer.Asortymenty a
                            JOIN ModelDanychContainer.JednostkiMiarAsortymentow jm ON jm.Asortyment_Id = a.Id
                            JOIN ModelDanychContainer.KodyKreskowe kk ON kk.JednostkaMiaryAsortymentu_Id = jm.Id
                            WHERE kk.Kod = @ean";
                using var cmd = new SqlCommand(sql, conn);
                cmd.Parameters.AddWithValue("@ean", req.EAN);
                var result = cmd.ExecuteScalar();
                if (result != null && result != DBNull.Value) return false; // istnieje po EAN â€” nie twĂłrz duplikatu
            }

            // 2. Szukaj po Symbol (SKU-Rozmiar) â€” jeĹ›li istnieje bez EAN, dodaj EAN i zakoĹ„cz
            if (!string.IsNullOrWhiteSpace(expectedSymbol) && !string.IsNullOrWhiteSpace(req.EAN))
            {
                using var conn = new SqlConnection(connStr);
                conn.Open();
                var sql = @"SELECT TOP 1 jm.Id FROM ModelDanychContainer.Asortymenty a
                            JOIN ModelDanychContainer.JednostkiMiarAsortymentow jm ON jm.Asortyment_Id = a.Id
                            WHERE a.Symbol = @symbol
                            AND NOT EXISTS (SELECT 1 FROM ModelDanychContainer.KodyKreskowe kk WHERE kk.JednostkaMiaryAsortymentu_Id = jm.Id)";
                using var cmd = new SqlCommand(sql, conn);
                cmd.Parameters.AddWithValue("@symbol", expectedSymbol);
                var jmId = cmd.ExecuteScalar();
                if (jmId != null && jmId != DBNull.Value)
                {
                    // Produkt istnieje po symbolu ale bez EAN â€” dodaj EAN
                    try
                    {
                        // ZnajdĹş produkt przez SferÄ™ i przypisz EAN
                        var asMgr2 = sfera.PodajObiektTypu<IAsortymenty>();
                        dynamic? towar2 = null;
                        foreach (dynamic a in asMgr2.Dane.Wszystkie())
                        {
                            if (a.Dane.Symbol == expectedSymbol) { towar2 = a; break; }
                        }
                        if (towar2 != null)
                        {
                            dynamic jm2 = towar2.Dane.PodstawowaJednostkaMiaryAsortymentu;
                            jm2.KodKreskowyOpakowania = req.EAN;
                            try
                            {
                                object jmObj = jm2;
                                var kkColl = jmObj.GetType().GetProperty("KodyKreskowe")?.GetValue(jmObj);
                                var collType = kkColl?.GetType();
                                if (collType != null && collType.IsGenericType)
                                {
                                    var genArg = collType.GetGenericArguments()[0];
                                    dynamic kodObj = Activator.CreateInstance(genArg)!;
                                    (genArg.GetProperty("Kod") ?? genArg.GetProperty("KodKreskowy"))?.SetValue((object)kodObj, req.EAN);
                                    collType.GetMethod("Add")?.Invoke(kkColl, new object[] { (object)kodObj });
                                }
                            }
                            catch { }
                            if (towar2.MoznaZapisac) towar2.Zapisz();
                            try { ((IDisposable)towar2).Dispose(); } catch { }
                        }
                    }
                    catch { }
                    return false; // produkt istnieje â€” nie twĂłrz nowego
                }
            }

            // 3. Nie znaleziono â€” sprawdĹş czy Symbol juĹĽ jest (ale z innym EAN? nie twĂłrz duplikatu symbolu)
            if (!string.IsNullOrWhiteSpace(expectedSymbol))
            {
                using var conn = new SqlConnection(connStr);
                conn.Open();
                using var cmd = new SqlCommand("SELECT TOP 1 Symbol FROM ModelDanychContainer.Asortymenty WHERE Symbol = @symbol", conn);
                cmd.Parameters.AddWithValue("@symbol", expectedSymbol);
                var r = cmd.ExecuteScalar();
                if (r != null && r != DBNull.Value) return false; // symbol zajÄ™ty przez inny EAN
            }

            var asMgr = sfera.PodajObiektTypu<IAsortymenty>();
            dynamic towar = asMgr.Utworz();

            dynamic? dzMgr = GetManager(sfera, "ISzablonyAsortymentu");
            if (dzMgr != null) towar.WypelnijNaPodstawieSzablonu(dzMgr.DaneDomyslne.Towar);

            towar.Dane.Symbol = expectedSymbol;
            towar.Dane.Nazwa = nazwaSubiekt;
            try { towar.Dane.Opis = opisSubiekt; } catch { }

            if (!string.IsNullOrWhiteSpace(req.EAN)) {
                try {
                    dynamic jm = towar.Dane.PodstawowaJednostkaMiaryAsortymentu;
                    jm.KodKreskowyOpakowania = req.EAN;
                    // Prosty przypis bez uĹĽycia strongly typed array
                    try {
                        object jmObj = jm;
                        var kkColl = jmObj.GetType().GetProperty("KodyKreskowe")?.GetValue(jmObj);
                        var collType = kkColl?.GetType();
                        if (collType != null && collType.IsGenericType) {
                            var genArg = collType.GetGenericArguments()[0];
                            dynamic kodObj = Activator.CreateInstance(genArg)!;
                            (genArg.GetProperty("Kod") ?? genArg.GetProperty("KodKreskowy"))?.SetValue((object)kodObj, req.EAN);
                            collType.GetMethod("Add")?.Invoke(kkColl, new object[] { (object)kodObj });
                        }
                    } catch { }
                } catch { }
            }

            // Ustaw VAT rate explicite (WypelnijNaPodstawieSzablonu moĹĽe nie dziaĹ‚aÄ‡ jeĹ›li brak szablonu)
            // Bez VAT rate: MoznaZapisac = false
            dynamic? vatMgr = GetManager(sfera, "IStawkiVat");
            if (vatMgr != null)
            {
                dynamic? vat23 = null;
                dynamic? vatFirst = null;
                foreach (dynamic vat in vatMgr.Dane.Wszystkie())
                {
                    try
                    {
                        if (vatFirst == null) vatFirst = vat;
                        if ((int)vat.Dane.Wartosc == 23) { vat23 = vat; break; }
                    }
                    catch { }
                }
                dynamic? vatToUse = vat23 ?? vatFirst;
                if (vatToUse != null)
                {
                    try { towar.Dane.StawkaVatSprzedazy = vatToUse; } catch { }
                    try { towar.Dane.StawkaVatZakupu = vatToUse; } catch { }
                }
            }

            if (!towar.MoznaZapisac)
            {
                Console.Error.WriteLine($"[WARN] EnsureProduct: MoznaZapisac=false dla {expectedSymbol} â€” pomijam ten rozmiar");
                try { ((IDisposable)towar).Dispose(); } catch { }
                return false; // nie blokuj caĹ‚ego ticketu
            }
            towar.Zapisz();
            try { ((IDisposable)towar).Dispose(); } catch { }

            if (!string.IsNullOrWhiteSpace(req.EAN)) {
                try {
                    using var conn = new SqlConnection(connStr);
                    conn.Open();
                    var sql = @"UPDATE ModelDanychContainer.KodyKreskowe
                                SET JednostkaMiaryAsortymentuZKodemPodstawowym_Id = JednostkaMiaryAsortymentu_Id
                                WHERE Kod = @ean AND JednostkaMiaryAsortymentuZKodemPodstawowym_Id IS NULL";
                    using var cmd = new SqlCommand(sql, conn);
                    cmd.Parameters.AddWithValue("@ean", req.EAN);
                    cmd.ExecuteNonQuery();
                } catch { }
            }

            return true;
        }

        static string CreatePZ(Uchwyt sfera, PzRequest req, string connStr)
        {
            var pzMgr = sfera.PodajObiektTypu<IPrzyjeciaZewnetrzne>();
            // VAT wariant — z tym działało Pozycje.Dodaj
            dynamic pz = pzMgr.UtworzPrzyjecieZewnetrzneVAT();


            // Ustaw dostawcę — próbuj PodmiotyDokumentu, fallback na Dane.Podmiot
            var podmioty = sfera.PodajObiektTypu<IPodmioty>();
            string? dostawcaSymbol = null;
            dynamic? dostawcaObj = null;
            foreach (dynamic p in podmioty.Dane.Wszystkie())
            {
                try { dostawcaSymbol = p.Sygnatura.PelnaSygnatura.ToString(); dostawcaObj = p; break; } catch { }
            }
            if (dostawcaSymbol != null)
            {
                bool podmiotSet = false;
                try { pz.PodmiotyDokumentu.UstawDostawceWedlugSymbolu(dostawcaSymbol); podmiotSet = true; } catch { }
                if (!podmiotSet && dostawcaObj != null)
                    try { pz.Dane.Podmiot = dostawcaObj; podmiotSet = true; } catch { }
                if (!podmiotSet && dostawcaObj != null)
                    try { pz.Dane.PodmiotWybrany = dostawcaObj; } catch { }
            }

            try { pz.Dane.DataDokumentu = DateTime.Today; } catch { }
            try { pz.Dane.DataOtrzymania = DateTime.Today; } catch { }
            // Status ustawiamy przez SQL po zapisie, nie przez SDK przed zapisem
            // (ustawienie statusu na nowym dok. może powodować MoznaZapisac=false)


            string numFaktury = req.NumerFakturyDostawcy ?? req.NumerZamowieniaZalando ?? "ZALANDO-AUTO";
            try { pz.Dane.NumerZewnetrzny = numFaktury; } catch { }
            try { pz.Dane.DataFakturyDostawcy = DateTime.Today; } catch { }
            if (!string.IsNullOrWhiteSpace(req.Uwagi)) try { pz.Dane.Uwagi = req.Uwagi; } catch { }

            dynamic? magMgr = GetManager(sfera, "IMagazyny");
            if (magMgr != null)
            {
                foreach (dynamic m in magMgr.Dane.Wszystkie()) { try { pz.Dane.Magazyn = m; } catch { } break; }
            }

            var asortymentMgr = sfera.PodajObiektTypu<IAsortymenty>();
            foreach (var item in req.Items)
            {
                dynamic produkt = null;

                // Szukaj po Symbol
                if (!string.IsNullOrWhiteSpace(item.Symbol))
                {
                    foreach (dynamic a in asortymentMgr.Dane.Wszystkie())
                    {
                        try { if (a.Symbol == item.Symbol) { produkt = a; break; } } catch { }
                    }
                }

                // Szukaj po EAN
                if (produkt == null && !string.IsNullOrWhiteSpace(item.EAN))
                {
                    var eanVariants = new[] { item.EAN, "0" + item.EAN };
                    foreach (dynamic a in asortymentMgr.Dane.Wszystkie()) {
                        try {
                            foreach (dynamic jm in a.JednostkiMiar) {
                                foreach (dynamic k in jm.KodyKreskowe) {
                                    foreach (var eanVar in eanVariants) {
                                        if (k.Kod == eanVar) { produkt = a; break; }
                                    }
                                    if (produkt != null) break;
                                }
                                if (produkt != null) break;
                            }
                            if (produkt != null) break;
                        } catch { }
                    }
                }

                if (produkt == null) throw new Exception($"Nie znaleziono produktu EAN={item.EAN} Symbol={item.Symbol}");

                // Dodaj pozycję — Sfera Dodaj() przyjmuje tylko Symbol (string), NIE EAN
                // produkt.Symbol = prawdziwy symbol w Subiekcie (np. HJ1985-010-43)
                // item.Symbol = SKU z zamówienia (np. HJ1985-010) — może być bez rozmiaru
                bool added = false;
                var dodajErrors = new System.Text.StringBuilder();
                // 1. symbol znalezionego produktu (pewny — pochodzi z Subiektu)
                try { pz.Pozycje.Dodaj(produkt.Symbol.ToString()); added = true; }
                catch (Exception ex1) { dodajErrors.Append($"PSYM:{ex1.Message}; "); }
                // 2. symbol z req (jeśli różni się od produktu)
                if (!added && !string.IsNullOrWhiteSpace(item.Symbol))
                    try { pz.Pozycje.Dodaj(item.Symbol); added = true; }
                    catch (Exception ex2) { dodajErrors.Append($"SYM:{ex2.Message}; "); }
                // 3. obiekt produktu z ilością decimal
                if (!added)
                    try { pz.Pozycje.Dodaj(produkt, item.Quantity); added = true; }
                    catch (Exception ex3) { dodajErrors.Append($"OBJ:{ex3.Message}; "); }
                // 4. obiekt produktu z ilością jako int
                if (!added)
                    try { pz.Pozycje.Dodaj(produkt, (int)item.Quantity); added = true; }
                    catch (Exception ex4) { dodajErrors.Append($"INT:{ex4.Message}; "); }
                if (!added)
                    throw new Exception($"Blad dodawania do PZ ({item.Symbol}/{item.EAN}): {dodajErrors}");



                // Ustaw ilość (Dodaj(ean) dodaje 1 szt.)
                dynamic lastPos = null;
                foreach (dynamic lp in (IEnumerable)pz.Dane.Pozycje) lastPos = lp;
                if (lastPos != null && item.Quantity != 1)
                    try { lastPos.Ilosc = (double)item.Quantity; } catch { try { lastPos.Ilosc = item.Quantity; } catch { } }


                if (item.CenaZakupu.HasValue)
                {
                    decimal cenaNetto = Math.Round(item.CenaZakupu.Value / 1.23m, 2);
                    if (lastPos != null) {
                        try { lastPos.Cena.NettoPrzedRabatem = cenaNetto; } catch { }
                        try { lastPos.Cena.NettoPoRabacie = cenaNetto; } catch { }
                    }
                }
            }



            try { pz.Przelicz(); } catch { }
            if (!pz.MoznaZapisac)
            {
                // Zbierz wszystkie dostępne info o błędzie
                var bledy = new System.Text.StringBuilder();
                try { foreach (dynamic b in pz.Bledy) bledy.Append(b.ToString()).Append("; "); } catch { }
                int pozycjiCount = 0;
                try { foreach (dynamic _ in (IEnumerable)pz.Dane.Pozycje) pozycjiCount++; } catch { }
                string bldMsg = bledy.Length > 0 ? bledy.ToString() : "(brak szczegółów)";
                throw new Exception($"Nie mozna zapisac PZ: {bldMsg} [dostawca={dostawcaSymbol ?? "brak"}, pozycji={pozycjiCount}]");
            }
            pz.Zapisz();

            string syg = pz.Dane.NumerWewnetrzny.PelnaSygnatura;
            int? pzDocId = null;
            try { pzDocId = (int)pz.Dane.Id; } catch { }
            try { ((IDisposable)pz).Dispose(); } catch { }

            // Ustaw status + FormaPlatnosciId (Przelew=2) + termin przez SQL (po zapisie)
            // WAZNE: pz.Dane.Id zwraca zly ID - szukamy przez NumerWewnetrzny_PelnaSygnatura
            if (!string.IsNullOrWhiteSpace(connStr) && !string.IsNullOrWhiteSpace(syg))
            {
                try
                {
                    using var connStat = new SqlConnection(connStr);
                    connStat.Open();
                    using (var qiCmd = new SqlCommand("SET QUOTED_IDENTIFIER ON", connStat)) qiCmd.ExecuteNonQuery();
                    // Znajdz wlasciwy Id przez sygnature PZ
                    int? realDocId = null;
                    using (var findCmd2 = new SqlCommand("SELECT Id FROM ModelDanychContainer.Dokumenty WHERE NumerWewnetrzny_PelnaSygnatura = @syg", connStat))
                    {
                        findCmd2.Parameters.AddWithValue("@syg", syg);
                        var val = findCmd2.ExecuteScalar();
                        if (val != null && val != DBNull.Value) realDocId = Convert.ToInt32(val);
                    }
                    if (realDocId.HasValue)
                    {
                        // Pobierz kwote dokumentu
                        decimal kwotaDoc = 0;
                        using (var kwotaCmd = new SqlCommand("SELECT KwotaDoZaplaty FROM ModelDanychContainer.Dokumenty WHERE Id=@id", connStat))
                        {
                            kwotaCmd.Parameters.AddWithValue("@id", realDocId.Value);
                            var kv = kwotaCmd.ExecuteScalar();
                            if (kv != null && kv != DBNull.Value) kwotaDoc = Convert.ToDecimal(kv);
                        }
                        // UPDATE Dokumenty: status(14=Odlozone przyjecie) + forma platnosci + termin
                        try {
                            using var cmdStat = new SqlCommand(
                                "UPDATE ModelDanychContainer.Dokumenty SET StatusDokumentuId=14, FormaPlatnosciId=2, DzienUstaleniaTerminuPlatnosci=14 WHERE Id=@id", connStat);
                            cmdStat.Parameters.AddWithValue("@id", realDocId.Value);
                            cmdStat.ExecuteNonQuery();
                        } catch { }


                    }
                    else syg += " [WARN: nie znaleziono Id dla syg]";
                }
                catch (Exception exSql) { syg += $" [SQL_ERR: {exSql.Message}]"; }
            }

            return syg;
        }

        static CliResponse UpdateTracking(string connStr, UpdateTrackingRequest req)
        {
            if (string.IsNullOrWhiteSpace(req.OrderName) || string.IsNullOrWhiteSpace(req.Tracking))
                return new CliResponse { Success = false, Message = "Brak orderName lub tracking" };

            using var conn = new SqlConnection(connStr);
            conn.Open();

            // ZnajdĹş PZ po uwagach zawierajÄ…cych orderName
            using var findCmd = new SqlCommand(@"
                SELECT TOP 1 Id, NumerPrzesylki, Uwagi
                FROM ModelDanychContainer.DokumentyPZ
                WHERE Uwagi LIKE @orderName
                ORDER BY DataDodania DESC", conn);
            findCmd.Parameters.AddWithValue("@orderName", $"%{req.OrderName}%");
            int? docId = null;
            using (var reader = findCmd.ExecuteReader())
            {
                if (reader.Read()) docId = reader.GetInt32(0);
            }

            if (!docId.HasValue)
                return new CliResponse { Success = false, Message = $"Nie znaleziono PZ dla zamĂłwienia: {req.OrderName}" };

            using var updateCmd = new SqlCommand(@"
                UPDATE ModelDanychContainer.DokumentyPZ
                SET NumerPrzesylki = @tracking,
                    Uwagi = Uwagi + ' | Tracking: ' + @tracking
                WHERE Id = @id", conn);
            updateCmd.Parameters.AddWithValue("@tracking", req.Tracking);
            updateCmd.Parameters.AddWithValue("@id", docId.Value);
            updateCmd.ExecuteNonQuery();

            return new CliResponse { Success = true, Message = $"Tracking zapisany do PZ docId={docId}" };
        }

        static CliResponse UpdateInvoice(Uchwyt sfera, string connStr, UpdateInvoiceRequest req)
        {
            if (string.IsNullOrWhiteSpace(req.OrderName) || string.IsNullOrWhiteSpace(req.InvoiceNumber))
                return new CliResponse { Success = false, Message = "Brak orderName lub invoiceNumber" };

            using var conn = new SqlConnection(connStr);
            conn.Open();

            // Znajdz Id i NumerWewnetrzny dokumentu PZ po uwagach
            using var findCmd = new SqlCommand(@"
                SELECT TOP 1 d.Id, d.NumerWewnetrzny_PelnaSygnatura FROM ModelDanychContainer.Dokumenty d
                WHERE d.Uwagi LIKE @orderName ORDER BY d.DataWprowadzenia DESC", conn);
            findCmd.Parameters.AddWithValue("@orderName", $"%{req.OrderName}%");
            int? docId = null;
            string docNumer = null;
            using (var reader = findCmd.ExecuteReader())
            {
                if (reader.Read()) { docId = reader.GetInt32(0); try { docNumer = reader.GetString(1); } catch { } }
            }

            if (!docId.HasValue)
                return new CliResponse { Success = false, Message = $"Nie znaleziono PZ dla: {req.OrderName}" };

            // SQL: ustaw tylko NumerZewnetrzny + Uwagi (data przez SDK ponizej)
            var sets = new System.Text.StringBuilder("SET NumerZewnetrzny = @invoiceNum");
            if (!string.IsNullOrWhiteSpace(req.Tracking)) sets.Append(", Uwagi = Uwagi + ' | FV: ' + @invoiceNum + ' | Tracking: ' + @tracking");
            else sets.Append(", Uwagi = Uwagi + ' | FV: ' + @invoiceNum");

            using var updateCmd = new SqlCommand($"UPDATE ModelDanychContainer.Dokumenty {sets} WHERE Id = @id", conn);
            updateCmd.Parameters.AddWithValue("@invoiceNum", req.InvoiceNumber);
            updateCmd.Parameters.AddWithValue("@id", docId.Value);
            if (!string.IsNullOrWhiteSpace(req.Tracking)) updateCmd.Parameters.AddWithValue("@tracking", req.Tracking);
            updateCmd.ExecuteNonQuery();

            // SDK: ustaw date faktury przez Sfera (DataFakturyDostawcy + DataOryginaluDokumentu)
            string sdkDateResult = "brak daty";
            if (!string.IsNullOrWhiteSpace(req.InvoiceDate) && DateTime.TryParse(req.InvoiceDate, out var invoiceDate))
            {
                try
                {
                    dynamic pzMgrDyn = GetManager(sfera, "IPrzyjeciaZewnetrzne");
                    dynamic pzBO = null;
                    if (pzMgrDyn != null)
                        foreach (dynamic pzData in pzMgrDyn.Dane.Wszystkie())
                            try { if ((int)pzData.Id == docId.Value) { pzBO = pzMgrDyn.Wczytaj(pzData); break; } } catch { }

                    if (pzBO != null)
                    {
                        try { pzBO.Dane.DataFakturyDostawcy = invoiceDate; } catch { }
                        try { pzBO.Dane.DataOryginaluDokumentu = invoiceDate; } catch { }
                        try { pzBO.Przelicz(); } catch { }
                        if (pzBO.MoznaZapisac) { pzBO.Zapisz(); sdkDateResult = $"data={invoiceDate:yyyy-MM-dd} ustawiona OK"; }
                        else sdkDateResult = "MoznaZapisac=false po ustawieniu daty";
                        try { ((IDisposable)pzBO).Dispose(); } catch { }
                    }
                    else sdkDateResult = "nie znaleziono PZ w SDK";
                }
                catch (Exception ex) { sdkDateResult = "blad SDK: " + ex.Message; }
            }

            return new CliResponse { Success = true, Message = $"PZ {docId} zaktualizowany: FV={req.InvoiceNumber} | {sdkDateResult}" };
        }
        static CliResponse AcceptPZ(Uchwyt sfera, string connStr, AcceptPzRequest req)
        {
            if (string.IsNullOrWhiteSpace(req.Tracking))
                return new CliResponse { Success = false, Message = "Brak numeru tracking" };

            using var conn = new SqlConnection(connStr);
            conn.Open();

            using var findCmd = new SqlCommand(@"
                SELECT TOP 1 Id, NumerWewnetrzny FROM ModelDanychContainer.DokumentyPZ
                WHERE NumerPrzesylki = @tracking OR Uwagi LIKE @trackingLike
                ORDER BY DataDodania DESC", conn);
            findCmd.Parameters.AddWithValue("@tracking", req.Tracking);
            findCmd.Parameters.AddWithValue("@trackingLike", $"%{req.Tracking}%");
            int? docId = null;
            string numWewn = "";
            using (var reader = findCmd.ExecuteReader())
            {
                if (reader.Read()) { docId = reader.GetInt32(0); numWewn = reader.GetString(1); }
            }

            if (!docId.HasValue)
                return new CliResponse { Success = false, Message = $"Nie znaleziono PZ z trackingiem: {req.Tracking}" };

            using var statusCmd = new SqlCommand(@"
                UPDATE ModelDanychContainer.DokumentyPZ SET Status_Id = 14 WHERE Id = @id", conn);
            statusCmd.Parameters.AddWithValue("@id", docId.Value);
            statusCmd.ExecuteNonQuery();

            return new CliResponse { Success = true, Sygnatura = numWewn, Message = $"PZ {numWewn} przyjety (tracking={req.Tracking})" };
        }

        static string CreateFZ(Uchwyt sfera, string connStr, FzRequest req)
        {
            // Znajdz ID PZ po OrderName w uwagach (przez dynamic - bez typed DokumentPZ)
            int? foundPzId = null;
            var pzMgr = sfera.PodajObiektTypu<IPrzyjeciaZewnetrzne>();
            if (!string.IsNullOrWhiteSpace(req.OrderName))
            {
                foreach (dynamic pzData in pzMgr.Dane.Wszystkie())
                {
                    try
                    {
                        string uwagi = pzData.Uwagi?.ToString() ?? "";
                        if (uwagi.Contains(req.OrderName)) { foundPzId = (int)pzData.Id; break; }
                    }
                    catch { }
                }
            }

            // Pobierz DokumentPZ (data object) przez Dane.Pierwszy
            // WypelnijNaPodstawiePZ wymaga DokumentPZ[], nie IPrzyjecieZewnetrzne BO
            dynamic pzFound = null;
            if (foundPzId.HasValue)
            {
                int targetId = foundPzId.Value;
                foreach (dynamic pz in pzMgr.Dane.Wszystkie())
                    try { if ((int)pz.Id == targetId) { pzFound = pz; break; } } catch { }
            }

            dynamic fzMgr = GetManager(sfera, "IDokumentyZakupu");
            if (fzMgr == null) throw new Exception("Nie znaleziono managera IDokumentyZakupu");

            dynamic fz = fzMgr.UtworzFaktureZakupu();

            if (pzFound != null)
            {
                var grupPars = new ParametryGrupowaniaDZ { MetodaGrupowaniaPozycji = MetodaGrupowaniaPozycji.BezKonsolidacji };
                var wypErr = new System.Text.StringBuilder();
                bool filled = false;
                try
                {
                    var pzArr = new DokumentPZ[] { (DokumentPZ)(object)pzFound };
                    fz.WypelnijNaPodstawiePZ(pzArr, (DokumentPZ)(object)pzFound, grupPars);
                    filled = true;
                }
                catch (Exception ex) { wypErr.Append("[typed]: " + ex.Message + "; "); }

                if (!filled)
                    throw new Exception("WypelnijNaPodstawiePZ nie powiodlo sie: " + wypErr);
            }
            else if (req.Items.Count > 0)
            {
                var asortymentMgr = sfera.PodajObiektTypu<IAsortymenty>();
                foreach (var item in req.Items)
                {
                    dynamic produkt = null;
                    if (!string.IsNullOrWhiteSpace(item.Symbol))
                        foreach (dynamic a in asortymentMgr.Dane.Wszystkie())
                            try { if (a.Symbol == item.Symbol) { produkt = a; break; } } catch { }
                    if (produkt == null) throw new Exception($"Nie znaleziono produktu Symbol={item.Symbol}");
                    try { fz.Pozycje.Dodaj(produkt, (double)item.Quantity); } catch { fz.Pozycje.Dodaj(produkt, item.Quantity); }
                }
            }
            else
            {
                throw new Exception($"Nie znaleziono PZ dla '{req.OrderName}' i brak items w req");
            }

            // Nadpisz numer i daty z faktury PDF
            if (!string.IsNullOrWhiteSpace(req.NumerFakturyDostawcy))
                try { fz.Dane.NumerZewnetrzny = req.NumerFakturyDostawcy; } catch { }
            if (!string.IsNullOrWhiteSpace(req.InvoiceDate) && DateTime.TryParse(req.InvoiceDate, out var invDate))
            {
                try { fz.Dane.DataDokumentu = invDate; } catch { }
                try { fz.Dane.DataFakturyDostawcy = invDate; } catch { }
                try { fz.Dane.DataOryginaluDokumentu = invDate; } catch { }
            }
            // Sprawdz czy mozna zapisac i zbierz bledy
            try { fz.Przelicz(); } catch { }
            var preBledy = new System.Text.StringBuilder();
            bool mozna = false;
            try { mozna = (bool)fz.MoznaZapisac; } catch { }
            if (!mozna)
            {
                try { foreach (dynamic b in fz.Bledy) preBledy.Append(b?.ToString()).Append("; "); } catch { }
                int pozFZ = 0;
                try { foreach (dynamic _ in (System.Collections.IEnumerable)fz.Dane.Pozycje) pozFZ++; } catch { }
                throw new Exception($"FZ MoznaZapisac=false [{preBledy}] pozycji={pozFZ}");
            }

            bool zapisano = false;
            try { zapisano = fz.Zapisz(); } catch (Exception exSave)
            {
                throw new Exception("Blad przy Zapisz() FZ: " + exSave.Message);
            }

            if (!zapisano)
            {
                // Zbierz bledy po nieudanym Zapisz() - mogą się pojawić dopiero tu
                var bledyPost = new System.Text.StringBuilder();
                try { foreach (dynamic b in fz.Bledy) bledyPost.Append("BLAD:").Append(b?.ToString()).Append("; "); } catch { }

                var bledy = new System.Text.StringBuilder();
                try
                {
                    foreach (dynamic encja in (System.Collections.IEnumerable)((dynamic)fz).InvalidData)
                    {
                        try { foreach (dynamic e in (System.Collections.IEnumerable)encja.Errors) bledy.Append("ERR:").Append(e).Append("; "); } catch { }
                        try { foreach (dynamic pair in (System.Collections.IEnumerable)encja.MemberErrors) bledy.Append("FIELD:").Append(pair.Key).Append("; "); } catch { }
                    }
                }
                catch { }
                int pozFZ = 0;
                try { foreach (dynamic _ in (System.Collections.IEnumerable)fz.Dane.Pozycje) pozFZ++; } catch { }
                string podmiotFZ = "?";
                try { podmiotFZ = fz.Dane.Podmiot?.NazwaSkrocona?.ToString() ?? "null"; } catch { }
                string allErr = (bledyPost.Length > 0 ? bledyPost.ToString() : "") + (bledy.Length > 0 ? bledy.ToString() : "");
                throw new Exception($"Zapisz() FZ false | pozycji={pozFZ} podmiot={podmiotFZ} | {(allErr.Length > 0 ? allErr : "(brak bledow walidacji)")}");
            }

            string sygFz = fz.Dane.NumerWewnetrzny.PelnaSygnatura;
            try { ((IDisposable)fz).Dispose(); } catch { }
            return sygFz;
        }
        static string CreateZK(Uchwyt sfera, ZkRequest req)
        {
            var podmiotyMgr = sfera.PodajObiektTypu<IPodmioty>();
            dynamic? klientData = null;
            foreach (dynamic p in podmiotyMgr.Dane.Wszystkie())
            {
                try { if ((string)p.NazwaSkrocona == req.CustomerName) { klientData = p; break; } } catch { }
            }
            if (klientData == null)
                throw new Exception($"Nie znaleziono klienta o NazwaSkrocona='{req.CustomerName}'");

            var walutyMgr = sfera.PodajObiektTypu<IWaluty>();
            dynamic? walutaEUR = null;
            foreach (dynamic w in walutyMgr.Dane.Wszystkie())
            {
                try { if ((string)w.Symbol == req.Currency) { walutaEUR = w; break; } } catch { }
            }
            if (walutaEUR == null)
                throw new Exception($"Nie znaleziono waluty '{req.Currency}'");

            var zkMgr = sfera.PodajObiektTypu<IZamowieniaOdKlientow>();
            dynamic? konfig = null;
            try { dynamic km = GetManager(sfera, "IKonfiguracje"); if (km != null) konfig = km.DaneDomyslne.ZamowienieOdKlienta; } catch { }

            dynamic zk = konfig != null ? zkMgr.Utworz(konfig) : zkMgr.Utworz();
            zk.Dane.Podmiot = klientData;
            try { zk.Dane.Waluta = walutaEUR; } catch { }
            if (!string.IsNullOrWhiteSpace(req.TicketName))
                try { zk.Dane.Uwagi = $"Ticket: {req.TicketName}"; } catch { }

            var asortymentMgr = sfera.PodajObiektTypu<IAsortymenty>();
            foreach (var item in req.Items)
            {
                dynamic? produkt = null;
                if (!string.IsNullOrWhiteSpace(item.EAN))
                {
                    try
                    {
                        produkt = asortymentMgr.Dane.Wszystkie().FirstOrDefault(a =>
                            a.JednostkiMiar.Any(j => j.KodyKreskowe.Any(k => k.Kod == item.EAN)));
                    }
                    catch
                    {
                        foreach (dynamic a in asortymentMgr.Dane.Wszystkie())
                        {
                            try
                            {
                                foreach (dynamic jm in a.JednostkiMiar)
                                    foreach (dynamic kk in jm.KodyKreskowe)
                                        if ((string)kk.Kod == item.EAN) { produkt = a; break; }
                                if (produkt != null) break;
                            } catch { }
                        }
                    }
                }
                if (produkt == null && !string.IsNullOrWhiteSpace(item.Symbol))
                    produkt = asortymentMgr.Dane.Wszystkie().FirstOrDefault(a => a.Symbol == item.Symbol);
                if (produkt == null)
                    throw new Exception($"Nie znaleziono produktu EAN={item.EAN} Symbol={item.Symbol}");

                try { zk.Pozycje.Dodaj(produkt, item.Quantity, produkt.JednostkaSprzedazy); }
                catch { try { zk.Pozycje.Dodaj(produkt, item.Quantity); } catch { zk.Pozycje.Dodaj(produkt, (double)item.Quantity); } }
            }

            try { zk.Przelicz(); } catch { }
            if (!zk.MoznaZapisac) throw new Exception("MoznaZapisac=false dla ZK");
            zk.Zapisz();
            string sygZk = zk.Dane.NumerWewnetrzny.PelnaSygnatura;
            try { ((IDisposable)zk).Dispose(); } catch { }
            return sygZk;
        }

        static string UpdatePzPositions(Uchwyt sfera, string connStr, UpdatePzRequest req)
        {
            if (string.IsNullOrWhiteSpace(req.PzSygnatura))
                throw new Exception("Brak PzSygnatura");

            // ZnajdĹş PZ po sygnaturze przez SQL (szybciej niĹĽ SDK)
            int pzId = -1;
            using (var con = new SqlConnection(connStr))
            {
                con.Open();
                using var cmd = new SqlCommand(
                    "SELECT TOP 1 dok_Id FROM Dokument WHERE dok_NumerPelny = @sig", con);
                cmd.Parameters.AddWithValue("@sig", req.PzSygnatura);
                var obj = cmd.ExecuteScalar();
                if (obj == null || obj == DBNull.Value)
                    throw new Exception($"Nie znaleziono PZ o sygnaturze '{req.PzSygnatura}'");
                pzId = Convert.ToInt32(obj);
            }

            // Otwórz PZ przez Sfera SDK (dynamicznie — Wczytaj wymaga konkretnego typu)
            dynamic pzMgrDyn = GetManager(sfera, "IPrzyjeciaZewnetrzne")
                ?? throw new Exception("Brak managera IPrzyjeciaZewnetrzne");
            dynamic? pz = null;
            foreach (dynamic p in pzMgrDyn.Dane.Wszystkie())
            {
                try { if ((int)p.Id == pzId) { pz = pzMgrDyn.Wczytaj(p); break; } } catch { }
            }
            if (pz == null)
                throw new Exception($"SDK: nie znaleziono PZ id={pzId}");

            var asortymentMgr = sfera.PodajObiektTypu<IAsortymenty>();
            var eansToUpdate = req.Items.ToDictionary(i => i.EAN ?? "", i => i.QtyToSubtract);
            int updated = 0;

            // Zbierz pozycje do modyfikacji/usuniÄ™cia
            var toRemove = new List<dynamic>();
            var toUpdate = new List<(dynamic poz, decimal newQty)>();

            foreach (dynamic poz in pz.Pozycje)
            {
                try
                {
                    // ZnajdĹş EAN pozycji
                    string? ean = null;
                    try
                    {
                        foreach (dynamic jm in poz.Asortyment.JednostkiMiar)
                            foreach (dynamic kk in jm.KodyKreskowe)
                            { ean = (string)kk.Kod; break; }
                    } catch { }

                    if (ean == null || !eansToUpdate.ContainsKey(ean)) continue;

                    decimal curQty = (decimal)poz.Ilosc;
                    decimal delta = eansToUpdate[ean];
                    decimal newQty = curQty - delta;

                    if (newQty <= 0)
                        toRemove.Add(poz);
                    else
                        toUpdate.Add((poz, newQty));

                    updated++;
                }
                catch { }
            }

            foreach (var poz in toRemove)
                try { pz.Pozycje.Usun(poz); } catch { }

            foreach (var (poz, newQty) in toUpdate)
                try { poz.Ilosc = newQty; } catch { }

            try { pz.Przelicz(); } catch { }
            if (!pz.MoznaZapisac) throw new Exception("MoznaZapisac=false po UpdatePzPositions");
            pz.Zapisz();
            try { ((IDisposable)pz).Dispose(); } catch { }

            return $"Zaktualizowano {updated} pozycji w {req.PzSygnatura}";
        }
    }
}
