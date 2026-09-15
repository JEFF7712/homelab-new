{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.homelab.kiosk;
  kioskBrowser = pkgs.writeShellScript "kiosk-browser" ''
    exec ${pkgs.chromium}/bin/chromium \
      --ozone-platform=wayland \
      --enable-features=UseOzonePlatform \
      --no-first-run \
      --noerrdialogs \
      --disable-infobars \
      --disable-features=Translate,OverlayScrollbar \
      --check-for-update-interval=31536000 \
      --password-store=basic \
      --disable-session-crashed-bubble \
      --incognito \
      --kiosk \
      "${cfg.url}"
  '';
in
{
  options.homelab.kiosk = {
    enable = lib.mkEnableOption "homelab kiosk display using cage and chromium";

    url = lib.mkOption {
      type = lib.types.str;
      default = "http://10.0.40.12/d/efa86fd1d0c121a26444b636a3f509a8?kiosk";
      description = "URL to display on the kiosk screen";
    };

    drmDevice = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = "/dev/dri/card1";
      description = "DRM device for cage/wlroots to bind to";
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = "kiosk";
      description = "System user to run cage and browser under";
    };
  };

  config = lib.mkIf cfg.enable {
    users.users.${cfg.user} = {
      isNormalUser = true;
      uid = 1001;
      group = cfg.user;
      extraGroups = [
        "video"
        "input"
      ];
      createHome = true;
      home = "/home/${cfg.user}";
    };
    users.groups.${cfg.user} = {
      gid = 1001;
    };

    fonts.packages = with pkgs; [
      dejavu_fonts
      freefont_ttf
      noto-fonts
      noto-fonts-color-emoji
    ];

    services.cage = {
      enable = true;
      user = cfg.user;
      extraArguments = [ "-s" ];
      environment = {
        WLR_LIBINPUT_NO_DEVICES = "1";
        WLR_NO_HARDWARE_CURSORS = "1";
        XDG_RUNTIME_DIR = "/run/user/1001";
      }
      // (lib.optionalAttrs (cfg.drmDevice != null) {
        WLR_DRM_DEVICES = cfg.drmDevice;
      });
      program = kioskBrowser;
    };

    systemd.services."cage-tty1" = {
      wantedBy = [ "multi-user.target" ];
      restartIfChanged = lib.mkForce true;
      serviceConfig = {
        Restart = "always";
        RestartSec = "3s";
      };
    };

    boot.kernelParams = [ "consoleblank=0" ];
  };
}
