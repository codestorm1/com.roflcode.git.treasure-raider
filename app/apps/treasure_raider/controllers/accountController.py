from google.appengine.ext import db

import logging

from datetime import datetime
from datetime import timedelta

from pyramid.main.models import Account
from pyramid.main.models import Account_transfer
from pyramid.main.models import Daily_reward
from pyramid.main.models import Reward_entry


class AccountController(object):
    
    def transfer_currency(self, source, target, amount):
        if source.balance < amount and not source.negative_balance_allowed:
            return None
        if source.currency_type != target.currency_type:
            return None
        source.balance -= amount
        transfer = Account_transfer(parent=source,
                            key_name=str(target.key()),
                            self_account=source,
                            counter_account=target,
                            counter_transfer=None,
                            currency_type=source.currency_type,
                            amount=amount,
                            is_committed = False)
        db.put([source, transfer])
        return transfer

    def transfer_currency_in_txn(self, source, target, amount):
        return db.run_in_transaction(self.transfer_currency, source, target, amount)            

    
    def roll_forward_account_transfer(self, source_transfer):
        def _tx():
            dest_transfer = Account_transfer.get_by_key_name(str(source_transfer.key()), parent=source_transfer.counter_account.key())
            if not dest_transfer:
                dest_transfer = Account_transfer(
                    parent = source_transfer.counter_account.key(),
                    key_name = str(source_transfer.key()),
                    self_account = source_transfer.counter_account,
                    counter_account = source_transfer.key().parent(), #same as source_transfer.counter_account
                    counter_transfer = source_transfer,
                    currency_type = source_transfer.currency_type,
                    amount = -source_transfer.amount,
                    is_committed = True)
                account = Account.get(dest_transfer.self_account.key())
                account.balance += source_transfer.amount # add negative amount
                db.put([account, dest_transfer])
            return dest_transfer
        dest_transfer = db.run_in_transaction(_tx)
        source_transfer.counter_transfer = dest_transfer
        source_transfer.is_committed = True
        source_transfer.put()

    def execute_uncommitted_account_transfers(self, count):
        rolled_count = 0
        cutoff = datetime.utcnow() - timedelta(seconds=30)
        q = Account_transfer.all().filter("is_committed =", False).filter("timestamp <", cutoff)
        for transfer in q.fetch(count):
            self.roll_forward_account_transfer(transfer)
            rolled_count += 1
        return rolled_count
