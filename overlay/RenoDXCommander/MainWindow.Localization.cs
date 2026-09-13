using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using RenoDXCommander.Services;

namespace RenoDXCommander;

public sealed partial class MainWindow
{
    private async void LanguageSystem_Click(object sender, RoutedEventArgs e)
    {
        LocalizationService.SavePreferredLanguage(UiLanguage.Auto);
        await ShowLanguageRestartNoticeAsync();
    }

    private async void LanguageEnglish_Click(object sender, RoutedEventArgs e)
    {
        LocalizationService.SavePreferredLanguage(UiLanguage.English);
        await ShowLanguageRestartNoticeAsync();
    }

    private async void LanguageChinese_Click(object sender, RoutedEventArgs e)
    {
        LocalizationService.SavePreferredLanguage(UiLanguage.SimplifiedChinese);
        await ShowLanguageRestartNoticeAsync();
    }

    private async Task ShowLanguageRestartNoticeAsync()
    {
        if (Content?.XamlRoot == null) return;
        var dialog = new ContentDialog
        {
            Title = "Language preference saved.",
            Content = "Restart RHI to apply the selected interface language.",
            CloseButtonText = "OK",
            XamlRoot = Content.XamlRoot,
        };
        await DialogService.ShowSafeAsync(dialog);
    }
}
