terraform {
  backend "gcs" {
    bucket = "aef-shahcago-hackathon-tfe"
    prefix = "aef-data-orchestration/environments/dev"
  }
}