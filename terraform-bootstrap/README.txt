1. Replace REPLACE_WITH_UNIQUE_TF_STATE_BUCKET_NAME with a globally unique bucket name.
2. Run:
   terraform init
   terraform apply
3. Copy outputs:
   tf_state_bucket
   tf_lock_table
4. Create GitHub repository secrets:
   TF_STATE_BUCKET=<bucket output>
   TF_LOCK_TABLE=<table output>
5. Re-run infra.yml
