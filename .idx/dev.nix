{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; # or "unstable"
  
  # Use https://search.nixos.org/packages to find packages
  packages = [ 
    pkgs.python3
    pkgs.mysql-client  # Este es el paquete correcto para mysqlclient en Nix
    pkgs.pkg-config   # Para resolver los errores de pkg-config no encontrado
  ];
  
  services.mysql = {
    enable = true;
    package = pkgs.mysql80;
  };
  
  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [ "ms-python.python" ];
    
    workspace = {
      # Runs when a workspace is first created with this `dev.nix` file
      onCreate = {
        install =
          "python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt";
        # Open editors for the following files by default, if they exist:
        default.openFiles = [ "README.md" "src/index.html" "main.py" ];
      };
      # To run something each time the workspace is (re)started, use the `onStart` hook
    };
    
    # Enable previews and customize configuration
    previews = {
      enable = true;
      previews = {
        web = {
          command = [ "./devserver.sh" ];
          env = { PORT = "$PORT"; };
          manager = "web";
        };
      };
    };
  };
}