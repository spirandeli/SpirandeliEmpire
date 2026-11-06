<?php

namespace App\Enums;

enum ApprovalStatus: string
{
    case Pending = 'pending';
    case RevisionRequested = 'revision_requested';
    case Revising = 'revising';
    case Approved = 'approved';
    case Scheduled = 'scheduled';
    case Rejected = 'rejected';
    case Expired = 'expired';

    /** Estados em que o usuário ainda pode decidir (aprovar / ajustar / descartar). */
    public function isReviewable(): bool
    {
        return in_array($this, [self::Pending, self::RevisionRequested], true);
    }

    public function isFinal(): bool
    {
        return in_array($this, [self::Approved, self::Scheduled, self::Rejected, self::Expired], true);
    }
}
