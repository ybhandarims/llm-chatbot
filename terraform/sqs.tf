resource "aws_sqs_queue" "ai_jobs_dlq" {
  name                        = "ai-jobs-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  tags                        = var.tags
}

resource "aws_sqs_queue" "ai_jobs" {
  name                        = "ai-jobs.fifo"
  fifo_queue                  = true
  content_based_deduplication = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ai_jobs_dlq.arn
    maxReceiveCount     = 5
  })

  tags = var.tags
}
