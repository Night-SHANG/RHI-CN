using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using WinUI3Localizer;

namespace RenoDXCommander.Services;

public static class UiLanguage
{
    public const string Auto = "auto";
    public const string English = "en-US";
    public const string SimplifiedChinese = "zh-CN";

    public static string Normalize(string? language)
    {
        if (string.IsNullOrWhiteSpace(language)) return Auto;
        return language.Trim().ToLowerInvariant() switch
        {
            "auto" or "system" => Auto,
            "en" or "english" or "en-us" => English,
            "zh" or "zh-cn" or "zh-hans" or "simplified chinese" => SimplifiedChinese,
            _ => Auto,
        };
    }

    public static string Resolve(string? preference)
    {
        var normalized = Normalize(preference);
        if (normalized != Auto) return normalized;
        var culture = CultureInfo.CurrentUICulture;
        return culture.Name.Equals("zh-CN", StringComparison.OrdinalIgnoreCase)
            || culture.Name.StartsWith("zh-Hans", StringComparison.OrdinalIgnoreCase)
            ? SimplifiedChinese
            : English;
    }
}

public static class LocalizationService
{
    private static string ExecutableDirectory =>
        Path.GetDirectoryName(Environment.ProcessPath) ?? AppContext.BaseDirectory;

    public static string StringsFolderPath => Path.Combine(ExecutableDirectory, "Strings");

    public static string PreferenceFilePath => Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "RHI",
        "ui-language.txt");

    public static string LoadPreferredLanguage()
    {
        try
        {
            return File.Exists(PreferenceFilePath)
                ? UiLanguage.Normalize(File.ReadAllText(PreferenceFilePath).Trim())
                : UiLanguage.Auto;
        }
        catch
        {
            return UiLanguage.Auto;
        }
    }

    public static void SavePreferredLanguage(string language)
    {
        try
        {
            var normalized = UiLanguage.Normalize(language);
            var parent = Path.GetDirectoryName(PreferenceFilePath)!;
            Directory.CreateDirectory(parent);
            File.WriteAllText(PreferenceFilePath, normalized);
        }
        catch (Exception ex)
        {
            try { CrashReporter.WriteCrashReport("LocalizationService.SavePreferredLanguage", ex); }
            catch { }
        }
    }

    public static async Task<bool> InitializeAsync()
    {
        try
        {
            _ = await new LocalizerBuilder()
                .AddStringResourcesFolderForLanguageDictionaries(StringsFolderPath)
                .SetOptions(options => options.DefaultLanguage = UiLanguage.Resolve(LoadPreferredLanguage()))
                .Build();
            return true;
        }
        catch (Exception ex)
        {
            try { CrashReporter.WriteCrashReport("LocalizationService.InitializeAsync", ex); }
            catch { }
            return false;
        }
    }

    public static string GetDataString(string? source)
    {
        if (string.IsNullOrEmpty(source)) return source ?? string.Empty;
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(source))).ToLowerInvariant()[..16];
        return GetString($"Data_{hash}", source);
    }

    public static string GetString(string key, string fallback = "")
    {
        try
        {
            var value = Localizer.Get().GetLocalizedString(key);
            return string.IsNullOrWhiteSpace(value) ? fallback : value;
        }
        catch
        {
            return fallback;
        }
    }
}
