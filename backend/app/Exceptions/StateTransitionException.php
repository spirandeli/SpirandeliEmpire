<?php

namespace App\Exceptions;

use RuntimeException;

/** Lançada quando uma operação não é permitida no estado atual do recurso (HTTP 409). */
class StateTransitionException extends RuntimeException
{
}

